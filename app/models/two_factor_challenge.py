from datetime import datetime

from app.extensions import db


class TwoFactorChallenge(db.Model):
    __tablename__ = "two_factor_challenges"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    token_hash = db.Column(db.String(64), nullable=False, unique=True)
    purpose = db.Column(db.String(30), nullable=False, index=True)
    method = db.Column(db.String(20), nullable=False)
    code_hash = db.Column(db.String(255), nullable=True)
    totp_secret_encrypted = db.Column(db.Text, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    attempt_count = db.Column(db.Integer, nullable=False, default=0)
    send_count = db.Column(db.Integer, nullable=False, default=0)
    last_sent_at = db.Column(db.DateTime, nullable=True)
    consumed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    user = db.relationship(
        "User",
        back_populates="two_factor_challenges"
    )
