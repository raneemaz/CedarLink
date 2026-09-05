from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy.orm import selectinload
from app.extensions import db
from app.models.store import Store
from app.models.store_announcement import StoreAnnouncement
from app.services import announcement_service, notification_service, store_service
from app.services.announcement_service import AnnouncementError
from app.services.store_service import SocialLinkError, StoreHoursError
from app.utils.decorators import role_required
from app.utils.geo import CoordinateError, validate_coords

store_bp = Blueprint("store", __name__, url_prefix="/api/stores")


def _store_with_status(store):
    """Store payload for the storefront — adds the live open/closed flag.

    ``next_opening_time`` rides along only when the store is shut and can
    still take an order: that is the one case the interface has to say
    something more than "closed", and computing it for every open store in
    a directory listing would be work nobody reads.
    """
    open_now, reason = store_service.is_open_now(store)

    payload = {**store.to_dict(), "is_open_now": open_now}

    if (
        not open_now
        and reason == store_service.CLOSED_OUTSIDE_HOURS
        and store.accepts_orders_when_closed
    ):
        opens_at = store_service.next_opening_time(store)
        payload["next_opening_time"] = (
            opens_at.isoformat() if opens_at else None
        )

    return payload


def _load_owned_store(store_id):
    """(store, None) when the caller owns it, else (None, (body, code))."""
    store = db.session.get(Store, store_id)
    if not store:
        return None, (jsonify({"message": "Store not found"}), 404)
    if int(store.owner_id) != int(get_jwt_identity()):
        return None, (
            jsonify({"message": "You can only manage your own store"}),
            403,
        )
    return store, None


@store_bp.route("", methods=["POST"])
@role_required("vendor")
def create_store():
    data = request.get_json()

    if not data:
        return jsonify({"message": "Request body is required"}), 400

    required_fields = ["name", "description", "location", "contact_info",
                       "inside_city_delivery_fee", "outside_city_delivery_fee"]

    for field in required_fields:
        value = data.get(field)

        if value is None or str(value).strip() == "":
            return jsonify({"message": f"{field} is required"}), 400

    user_id = int(get_jwt_identity())

    try:
        inside_fee = float(data["inside_city_delivery_fee"])
        outside_fee = float(data["outside_city_delivery_fee"])

        if inside_fee < 0 or outside_fee < 0:
            return jsonify({
                "message": "Delivery fees cannot be negative"
            }), 400

    except (TypeError, ValueError):
        return jsonify({
            "message": "Delivery fees must be numeric"
        }), 400

    store = Store(
        owner_id=user_id,
        name=data["name"],
        description=data["description"],
        location=data["location"],
        contact_info=data["contact_info"],
        inside_city_delivery_fee=inside_fee,
        outside_city_delivery_fee=outside_fee,
    )

    db.session.add(store)
    db.session.commit()

    return jsonify({
        "message": "Store created successfully",
        "store": store_service.owner_store_dict(store)
    }), 201


@store_bp.route("", methods=["GET"])
def get_stores():
    """Public store directory — approved, active, non-removed stores only.

    Query params: keyword (name match), location (exact, case-insensitive),
    page, limit, sort=name|newest. Add ``near=lat,lng`` (with optional
    ``radius`` in km, default 5) for a distance search: results are then
    ordered nearest-first and each carries ``distance_km``. Without
    ``near`` the behaviour is exactly as before. The customer's
    coordinates are used for this one request and never logged.
    Response shape mirrors GET /api/products.
    """
    # selectinload the week's schedule: _store_with_status() calls
    # is_open_now() for every row, which walks store.hours. Without this the
    # directory fires one extra SELECT per store (CL-18).
    query = Store.query.options(selectinload(Store.hours)).filter(
        Store.is_visible
    )

    keyword = request.args.get("keyword", "").strip()
    if keyword:
        query = query.filter(Store.name.ilike(f"%{keyword}%"))

    location = request.args.get("location", "").strip()
    if location:
        query = query.filter(
            db.func.lower(Store.location) == location.lower()
        )

    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("limit", 10))
    except (TypeError, ValueError):
        return jsonify({
            "message": "page and limit must be integers"
        }), 400

    if page < 1 or per_page < 1:
        return jsonify({
            "message": "page and limit must be greater than 0"
        }), 400

    near = request.args.get("near", "").strip()
    if near:
        return _get_stores_near(query, near, page, per_page)

    if request.args.get("sort") == "newest":
        query = query.order_by(Store.id.desc())
    else:
        query = query.order_by(Store.name.asc())

    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    return jsonify({
        "stores": [_store_with_status(store) for store in pagination.items],
        "page": pagination.page,
        "pages": max(pagination.pages, 1),
        "total": pagination.total
    }), 200


def _get_stores_near(query, near, page, per_page):
    """Distance-search branch of the directory. ``query`` already carries
    the visibility / keyword / location filters."""
    parts = near.split(",")
    if len(parts) != 2:
        return jsonify({"message": "near must be 'latitude,longitude'"}), 400

    try:
        center = validate_coords(parts[0].strip(), parts[1].strip())
    except CoordinateError as exc:
        return jsonify({"message": str(exc)}), 400

    if center[0] is None:
        return jsonify({"message": "near must be 'latitude,longitude'"}), 400

    try:
        radius_km = float(request.args.get("radius", 5))
    except (TypeError, ValueError):
        return jsonify({"message": "radius must be a number"}), 400

    if not 0 < radius_km <= store_service.MAX_RADIUS_KM:
        return jsonify({
            "message": (
                "radius must be between 0 and "
                f"{store_service.MAX_RADIUS_KM:g} km"
            )
        }), 400

    ranked = store_service.nearby(*center, radius_km, query=query)

    total = len(ranked)
    start = (page - 1) * per_page
    window = ranked[start:start + per_page]

    return jsonify({
        "stores": [
            {**_store_with_status(store), "distance_km": distance}
            for store, distance in window
        ],
        "page": page,
        "pages": max((total + per_page - 1) // per_page, 1),
        "total": total,
    }), 200


@store_bp.route("/<int:store_id>", methods=["GET"])
def get_store(store_id):
    store = db.session.get(Store, store_id)

    # Deactivated or admin-removed stores are absent from the public
    # storefront. The owning vendor manages theirs via /api/vendor/store.
    if not store or not store.is_visible:
        return jsonify({"message": "Store not found"}), 404

    return jsonify({
        "store": _store_with_status(store)
    }), 200


@store_bp.route("/<int:store_id>", methods=["PUT"])
@role_required("vendor")
def update_store(store_id):
    store = db.session.get(Store, store_id)

    if not store:
        return jsonify({"message": "Store not found"}), 404

    current_user = int(get_jwt_identity())

    if int(store.owner_id) != current_user:
        return jsonify({
            "message": "You can only update your own store"
        }), 403

    data = request.get_json()

    if not data:
        return jsonify({"message": "Request body is required"}), 400

    if "name" in data:
        if not str(data["name"]).strip():
            return jsonify({"message": "name cannot be empty"}), 400
        store.name = data["name"]

    if "description" in data:
        if not str(data["description"]).strip():
            return jsonify({"message": "description cannot be empty"}), 400
        store.description = data["description"]

    if "location" in data:
        if not str(data["location"]).strip():
            return jsonify({"message": "location cannot be empty"}), 400
        store.location = data["location"]

    if "contact_info" in data:
        if not str(data["contact_info"]).strip():
            return jsonify({"message": "contact_info cannot be empty"}), 400
        store.contact_info = data["contact_info"]

    if "inside_city_delivery_fee" in data:
        try:
            fee = float(data["inside_city_delivery_fee"])

            if fee < 0:
                return jsonify({
                    "message": "Inside city delivery fee cannot be negative"
                }), 400

            store.inside_city_delivery_fee = fee

        except (TypeError, ValueError):
            return jsonify({
                "message": "Invalid inside city delivery fee"
            }), 400

    if "outside_city_delivery_fee" in data:
        try:
            fee = float(data["outside_city_delivery_fee"])

            if fee < 0:
                return jsonify({
                    "message": "Outside city delivery fee cannot be negative"
                }), 400

            store.outside_city_delivery_fee = fee

        except (TypeError, ValueError):
            return jsonify({
                "message": "Invalid outside city delivery fee"
            }), 400

    if "delivery_available" in data:
        if not isinstance(data["delivery_available"], bool):
            return jsonify({
                "message": "delivery_available must be true or false"
            }), 400

        store.delivery_available = data["delivery_available"]

    if "accepts_orders_when_closed" in data:
        if not isinstance(data["accepts_orders_when_closed"], bool):
            return jsonify({
                "message": "accepts_orders_when_closed must be true or false"
            }), 400

        store.accepts_orders_when_closed = data["accepts_orders_when_closed"]

    if "is_online_only" in data:
        if not isinstance(data["is_online_only"], bool):
            return jsonify({
                "message": "is_online_only must be true or false"
            }), 400

        # Turning it on clears the map pin (store_service).
        store_service.set_online_only(store, data["is_online_only"])

    db.session.commit()

    return jsonify({
        "message": "Store updated successfully",
        "store": store_service.owner_store_dict(store)
    }), 200


@store_bp.route("/<int:store_id>/status", methods=["PATCH"])
@role_required("vendor")
def toggle_store_status(store_id):
    store = db.session.get(Store, store_id)

    if not store:
        return jsonify({
            "message": "Store not found"
        }), 404

    current_user = int(get_jwt_identity())

    if int(store.owner_id) != current_user:
        return jsonify({
            "message": "You can only update your own store"
        }), 403

    data = request.get_json()

    if not data:
        return jsonify({
            "message": "Request body is required"
        }), 400

    if "is_active" not in data:
        return jsonify({
            "message": "is_active is required"
        }), 400

    if not isinstance(data["is_active"], bool):
        return jsonify({
            "message": "is_active must be true or false"
        }), 400

    store.is_active = data["is_active"]

    db.session.commit()

    return jsonify({
        "message": "Store status updated successfully",
        "store": store_service.owner_store_dict(store)
    }), 200


# --------------------------------------------------------------------------- #
# Location (map pin)
# --------------------------------------------------------------------------- #

@store_bp.route("/<int:store_id>/location", methods=["PUT"])
@role_required("vendor")
def set_store_location(store_id):
    store, error = _load_owned_store(store_id)
    if error:
        return error

    data = request.get_json() or {}

    try:
        store_service.set_location(
            store, data.get("latitude"), data.get("longitude")
        )
    except CoordinateError as exc:
        return jsonify({"message": str(exc)}), 400

    db.session.commit()

    return jsonify({
        "message": "Location updated",
        "store": store_service.owner_store_dict(store),
    }), 200


# --------------------------------------------------------------------------- #
# Working hours
# --------------------------------------------------------------------------- #

@store_bp.route("/<int:store_id>/hours", methods=["GET"])
def get_store_hours(store_id):
    """Public — the store's weekly schedule (empty list for a closed day)."""
    store = db.session.get(Store, store_id)
    if not store or not store.is_visible:
        return jsonify({"message": "Store not found"}), 404

    return jsonify({
        "hours": [row.to_dict() for row in store.hours]
    }), 200


@store_bp.route("/<int:store_id>/hours", methods=["PUT"])
@role_required("vendor")
def set_store_hours(store_id):
    store, error = _load_owned_store(store_id)
    if error:
        return error

    data = request.get_json() or {}

    try:
        store_service.replace_hours(store, data.get("hours"))
    except StoreHoursError as exc:
        db.session.rollback()
        return jsonify({"message": str(exc)}), 400

    db.session.commit()

    return jsonify({
        "message": "Working hours updated",
        "hours": [row.to_dict() for row in store.hours],
    }), 200


# --------------------------------------------------------------------------- #
# Manual open/closed override
# --------------------------------------------------------------------------- #

@store_bp.route("/<int:store_id>/override", methods=["PATCH"])
@role_required("vendor")
def set_store_override(store_id):
    store, error = _load_owned_store(store_id)
    if error:
        return error

    data = request.get_json() or {}

    try:
        store_service.set_override(
            store,
            data.get("status"),
            data.get("reason"),
            data.get("duration"),
            data.get("until"),
        )
    except StoreHoursError as exc:
        return jsonify({"message": str(exc)}), 400

    db.session.commit()

    return jsonify({
        "message": "Override set",
        "store": store_service.owner_store_dict(store),
    }), 200


@store_bp.route("/<int:store_id>/override", methods=["DELETE"])
@role_required("vendor")
def clear_store_override(store_id):
    store, error = _load_owned_store(store_id)
    if error:
        return error

    store_service.clear_override(store)
    db.session.commit()

    return jsonify({
        "message": "Override cleared",
        "store": store_service.owner_store_dict(store),
    }), 200


# --------------------------------------------------------------------------- #
# Announcements
# --------------------------------------------------------------------------- #

def _load_announcement(store, aid):
    announcement = db.session.get(StoreAnnouncement, aid)
    if not announcement or announcement.store_id != store.id:
        return None, (jsonify({"message": "Announcement not found"}), 404)
    return announcement, None


@store_bp.route("/<int:store_id>/announcements", methods=["GET"])
@jwt_required(optional=True)
def get_store_announcements(store_id):
    """Live announcements for the public; every announcement for the owner."""
    store = db.session.get(Store, store_id)
    identity = get_jwt_identity()
    is_owner = bool(
        store and identity and int(store.owner_id) == int(identity)
    )

    if not store or (not store.is_visible and not is_owner):
        return jsonify({"message": "Store not found"}), 404

    if is_owner:
        rows = [
            announcement_service.serialize(a) for a in store.announcements
        ]
    else:
        rows = [
            a.to_dict()
            for a in announcement_service.live_for_store(store)
        ]

    return jsonify({"announcements": rows}), 200


@store_bp.route("/<int:store_id>/announcements", methods=["POST"])
@role_required("vendor")
def create_store_announcement(store_id):
    store, error = _load_owned_store(store_id)
    if error:
        return error

    try:
        announcement = announcement_service.create(
            store, request.get_json() or {}
        )
    except AnnouncementError as exc:
        db.session.rollback()
        return jsonify({"message": str(exc)}), 400

    db.session.commit()
    notification_service.notify_store_announcement(announcement)

    return jsonify({
        "message": "Announcement created",
        "announcement": announcement_service.serialize(announcement),
    }), 201


@store_bp.route(
    "/<int:store_id>/announcements/<int:aid>", methods=["PUT"]
)
@role_required("vendor")
def update_store_announcement(store_id, aid):
    store, error = _load_owned_store(store_id)
    if error:
        return error

    announcement, missing = _load_announcement(store, aid)
    if missing:
        return missing

    try:
        announcement_service.update(
            store, announcement, request.get_json() or {}
        )
    except AnnouncementError as exc:
        db.session.rollback()
        return jsonify({"message": str(exc)}), 400

    db.session.commit()

    return jsonify({
        "message": "Announcement updated",
        "announcement": announcement_service.serialize(announcement),
    }), 200


@store_bp.route(
    "/<int:store_id>/announcements/<int:aid>", methods=["DELETE"]
)
@role_required("vendor")
def delete_store_announcement(store_id, aid):
    store, error = _load_owned_store(store_id)
    if error:
        return error

    announcement, missing = _load_announcement(store, aid)
    if missing:
        return missing

    announcement_service.delete(announcement)
    db.session.commit()

    return jsonify({"message": "Announcement deleted"}), 200


# --------------------------------------------------------------------------- #
# Social and contact links
# --------------------------------------------------------------------------- #

@store_bp.route("/<int:store_id>/social-links", methods=["GET"])
def get_store_social_links(store_id):
    """Public — the store's links, already normalised and safe to render."""
    store = db.session.get(Store, store_id)
    if not store or not store.is_visible:
        return jsonify({"message": "Store not found"}), 404

    return jsonify({
        "social_links": store_service.social_links_payload(store)
    }), 200


@store_bp.route("/<int:store_id>/social-links", methods=["PUT"])
@role_required("vendor")
def set_store_social_links(store_id):
    """Owner only — replace the whole set in one transaction."""
    store, error = _load_owned_store(store_id)
    if error:
        return error

    data = request.get_json() or {}

    try:
        store_service.replace_social_links(store, data.get("social_links"))
    except SocialLinkError as exc:
        db.session.rollback()
        return jsonify({"message": str(exc)}), 400

    db.session.commit()

    return jsonify({
        "message": "Links updated",
        "social_links": store_service.social_links_payload(store),
    }), 200


@store_bp.route("/<int:store_id>/social-links/preview", methods=["POST"])
@role_required("vendor")
def preview_store_social_links(store_id):
    """Owner only — normalise a submission without writing it.

    The vendor form needs to show what ``@hamragrocery`` will become before
    the vendor commits to it. The alternative was a copy of the rules in
    JavaScript, which is the same mistake as a second column meaning the
    same thing: the two would drift, and the one that matters is this one.
    """
    store, error = _load_owned_store(store_id)
    if error:
        return error

    data = request.get_json() or {}
    entries = data.get("social_links")

    if entries is None:
        entries = []

    if not isinstance(entries, list):
        return jsonify({"message": "social_links must be a list"}), 400

    # Per entry, so one bad field does not hide the normalisation of the
    # good ones — the form marks up each row on its own.
    results = []

    for entry in entries:
        if not isinstance(entry, dict):
            return jsonify({"message": "Each social link must be an object"}), 400

        platform = entry.get("platform")
        raw = entry.get("value")

        if raw is None or (isinstance(raw, str) and not raw.strip()):
            results.append({"platform": platform, "value": None,
                            "error": None})
            continue

        try:
            results.append({
                "platform": platform,
                "value": store_service.normalize_social_value(platform, raw),
                "error": None,
            })
        except SocialLinkError as exc:
            results.append({
                "platform": platform,
                "value": None,
                "error": str(exc),
            })

    return jsonify({"social_links": results}), 200
