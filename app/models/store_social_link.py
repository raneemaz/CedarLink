from datetime import datetime, timezone

from app.extensions import db


def _utc_now_naive():
    """Current UTC as a naive datetime — the storage convention in this schema.

    ``datetime.now(timezone.utc)`` (never ``utcnow()``), tz dropped for the
    column, consistent with the rest of the store tables.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _utc_isoformat(value):
    """A stored naive-UTC datetime as an explicit-UTC ISO 8601 string."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


INSTAGRAM = "instagram"
FACEBOOK = "facebook"
TIKTOK = "tiktok"
WHATSAPP = "whatsapp"
WEBSITE = "website"
EMAIL = "email"
PHONE = "phone"

# The order the interface offers them in, vendor form and store page alike.
PLATFORMS = (
    INSTAGRAM,
    FACEBOOK,
    TIKTOK,
    WHATSAPP,
    WEBSITE,
    EMAIL,
    PHONE,
)

_PLATFORM_LIST = ", ".join(f"'{name}'" for name in PLATFORMS)


class StoreSocialLink(db.Model):
    """One way to reach a store — a profile, a site, an address, a number.

    ``value`` is always the finished, ready-to-render string: an
    ``https://`` URL for the profile platforms and the website, a
    ``mailto:`` for email, a ``tel:`` for phone. Normalisation happens in
    ``store_service.normalize_social_value`` before anything is written, so
    what a customer's browser follows was built by us out of the vendor's
    input rather than being the vendor's input. Only http and https ever
    reach the column — a vendor-supplied ``javascript:`` in an ``href`` is
    stored cross-site scripting against every customer who clicks it.

    One row per platform per store: the vendor form has a single field for
    each, so a second Instagram is a bug, not a second account. The unique
    index is what makes that true rather than the form.

    There is deliberately no ORM cascade: the store is soft-deleted, never
    row-deleted, so these rows persist with it — the same call ``hours``
    and ``announcements`` make in ``store.py``.
    """

    __tablename__ = "store_social_links"
    __table_args__ = (
        db.UniqueConstraint(
            "store_id", "platform", name="uq_store_social_links_store_platform"
        ),
        db.CheckConstraint(
            f"platform IN ({_PLATFORM_LIST})",
            name="ck_store_social_links_platform",
        ),
        db.Index("ix_store_social_links_store_id", "store_id"),
    )

    id = db.Column(db.Integer, primary_key=True)

    store_id = db.Column(
        db.Integer,
        db.ForeignKey("stores.id"),
        nullable=False,
    )

    platform = db.Column(db.String(20), nullable=False)

    value = db.Column(db.String(500), nullable=False)

    created_at = db.Column(
        db.DateTime, nullable=False, default=_utc_now_naive
    )

    store = db.relationship("Store", back_populates="social_links")

    def to_dict(self):
        return {
            "id": self.id,
            "store_id": self.store_id,
            "platform": self.platform,
            "value": self.value,
            "created_at": _utc_isoformat(self.created_at),
        }
