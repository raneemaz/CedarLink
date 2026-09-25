from datetime import datetime

from app.extensions import db


class IdempotencyKey(db.Model):
    """Guards a client-supplied key against being acted on twice.

    The client attaches the same key to every attempt of one logical
    action -- a double-click on "Place order", or a resend after a slow
    network made the first response time out before it arrived. The first
    request to claim a key runs the action normally; any later request
    carrying that same key gets back the exact response the first one
    produced, instead of repeating the action's side effects (a second
    order, a second charge).

    Scoped by (user_id, scope, key) rather than key alone: two different
    actions -- or two different users -- are free to reuse the same
    client-generated key without colliding with each other.
    """

    __tablename__ = "idempotency_keys"
    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "scope", "key",
            name="uq_idempotency_keys_user_scope_key"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    # The action this key belongs to, e.g. "checkout". Keys are only ever
    # compared within the same scope.
    scope = db.Column(db.String(50), nullable=False)

    key = db.Column(db.String(255), nullable=False)

    # in_progress -> completed (a real response was produced and cached)
    #             -> failed     (the action raised; a retry may try again)
    status = db.Column(
        db.String(20),
        nullable=False,
        default="in_progress"
    )

    response_status = db.Column(db.Integer, nullable=True)
    response_body = db.Column(db.Text, nullable=True)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
