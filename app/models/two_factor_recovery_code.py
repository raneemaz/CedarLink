from datetime import datetime

from app.extensions import db


class TwoFactorRecoveryCode(db.Model):
    __tablename__ = "two_factor_recovery_codes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    code_hash = db.Column(db.String(255), nullable=False)
    used = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    used_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship(
        "User",
        back_populates="two_factor_recovery_codes"
    )
