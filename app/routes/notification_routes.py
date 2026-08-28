from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.notification import Notification

notification_bp = Blueprint(
    "notifications", __name__, url_prefix="/api/notifications"
)

DEFAULT_LIMIT = 20
MAX_LIMIT = 50


def _unread_count(user_id):
    return Notification.query.filter_by(
        user_id=user_id, is_read=False
    ).count()


@notification_bp.route("", methods=["GET"])
@jwt_required()
def list_notifications():
    user_id = int(get_jwt_identity())

    try:
        limit = int(request.args.get("limit", DEFAULT_LIMIT))
    except (TypeError, ValueError):
        limit = DEFAULT_LIMIT

    try:
        offset = int(request.args.get("offset", 0))
    except (TypeError, ValueError):
        offset = 0

    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)

    unread_only = request.args.get("unread", "").lower() == "true"

    query = Notification.query.filter_by(user_id=user_id)

    if unread_only:
        query = query.filter_by(is_read=False)

    total = query.count()

    notifications = (
        query.order_by(
            Notification.created_at.desc(), Notification.id.desc()
        )
        .limit(limit)
        .offset(offset)
        .all()
    )

    return (
        jsonify(
            {
                "notifications": [n.to_dict() for n in notifications],
                "unread_count": _unread_count(user_id),
                "total": total,
                "limit": limit,
                "offset": offset,
            }
        ),
        200,
    )


@notification_bp.route("/unread-count", methods=["GET"])
@jwt_required()
def unread_count():
    user_id = int(get_jwt_identity())

    return jsonify({"unread_count": _unread_count(user_id)}), 200


@notification_bp.route("", methods=["DELETE"])
@jwt_required()
def delete_all_notifications():
    user_id = int(get_jwt_identity())

    deleted = Notification.query.filter_by(user_id=user_id).delete()

    db.session.commit()

    return (
        jsonify(
            {
                "message": "Notifications deleted successfully",
                "deleted": deleted,
            }
        ),
        200,
    )


@notification_bp.route("/read-all", methods=["PATCH"])
@jwt_required()
def mark_all_read():
    user_id = int(get_jwt_identity())

    updated = (
        Notification.query.filter_by(user_id=user_id, is_read=False).update(
            {
                "is_read": True,
                "read_at": datetime.utcnow(),
            }
        )
    )

    db.session.commit()

    return jsonify({"updated": updated, "unread_count": 0}), 200


@notification_bp.route("/<int:notification_id>/read", methods=["PATCH"])
@jwt_required()
def mark_read(notification_id):
    user_id = int(get_jwt_identity())

    notification = Notification.query.filter_by(
        id=notification_id, user_id=user_id
    ).first()

    if not notification:
        return jsonify({"message": "Notification not found"}), 404

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        db.session.commit()

    return (
        jsonify(
            {
                "notification": notification.to_dict(),
                "unread_count": _unread_count(user_id),
            }
        ),
        200,
    )
