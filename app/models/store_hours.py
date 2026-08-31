from app.extensions import db


class StoreHours(db.Model):
    """One opening interval for a store on one weekday.

    ``day_of_week`` is 0-6 with Monday = 0 (``datetime.weekday()``). A
    (store, day) pair may have zero or more rows; **zero rows means the store
    is closed that day** — there is deliberately no ``is_closed`` flag.

    Times are naive local wall-clock (Asia/Beirut). When ``closes_at`` is at
    or before ``opens_at`` the interval crosses midnight into the next day.
    See docs/decisions/0013-store-hours-timezone.md.

    Rows go away with the store through the ORM cascade below; the store
    itself is soft-deleted, so this never reaches order history.
    """

    __tablename__ = "store_hours"

    id = db.Column(db.Integer, primary_key=True)

    store_id = db.Column(
        db.Integer,
        db.ForeignKey("stores.id"),
        nullable=False,
        index=True,
    )

    day_of_week = db.Column(db.SmallInteger, nullable=False)

    opens_at = db.Column(db.Time, nullable=False)
    closes_at = db.Column(db.Time, nullable=False)

    store = db.relationship("Store", back_populates="hours")

    def to_dict(self):
        return {
            "id": self.id,
            "day_of_week": self.day_of_week,
            "opens_at": self.opens_at.strftime("%H:%M"),
            "closes_at": self.closes_at.strftime("%H:%M"),
        }

    def __repr__(self):
        return (
            f"<StoreHours store={self.store_id} day={self.day_of_week} "
            f"{self.opens_at}-{self.closes_at}>"
        )
