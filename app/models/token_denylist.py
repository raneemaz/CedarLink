from datetime import datetime, timezone

from app.extensions import db


class TokenDenylist(db.Model):
    """One row per individually-revoked JWT (a logout).

    Bulk revocation — password reset, admin suspension, self-deactivation —
    does not enumerate a user's outstanding tokens; it stamps
    ``User.tokens_revoked_at`` instead, and the blocklist loader rejects any
    token issued before that. See docs/decisions/0008-token-revocation.md.
    """

    __tablename__ = "token_denylist"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True, index=True)
    token_type = db.Column(db.String(10), nullable=False)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    # When the token would have expired anyway — lets a cleanup job prune
    # rows that can no longer matter.
    expires_at = db.Column(db.DateTime, nullable=False)
