from datetime import datetime, timezone

from app.extensions import db


def _utc_now():
    return datetime.now(timezone.utc)


def _utc_isoformat(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


class ReviewReport(db.Model):
    """One user's report of one review, with a reason.

    A user may report a given review at most once — the unique constraint is
    the backstop, ``review_service`` does the friendly pre-check. The row is
    kept after the review is moderated: it is the evidence the admin acted
    on, the same reason reviews and stores are soft-removed rather than
    deleted. See docs/decisions/0017-review-moderation.md.
    """

    __tablename__ = "review_reports"
    __table_args__ = (
        db.UniqueConstraint(
            "review_id", "user_id", name="uq_review_reports_review_user"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)

    review_id = db.Column(
        db.Integer,
        db.ForeignKey("reviews.id"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False
    )

    reason = db.Column(db.String(500), nullable=False)

    created_at = db.Column(db.DateTime, nullable=False, default=_utc_now)

    review = db.relationship("Review", back_populates="reports")
    user = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "review_id": self.review_id,
            "reason": self.reason,
            "created_at": _utc_isoformat(self.created_at),
            "reporter": {
                "id": self.user_id,
                "name": (
                    f"{self.user.first_name} {self.user.last_name}"
                    if self.user
                    else None
                ),
            },
        }
