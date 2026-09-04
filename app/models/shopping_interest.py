from app.extensions import db


class ShoppingInterest(db.Model):
    """One category a customer has said they care about.

    Explicit preference only — a row exists because the customer ticked a
    box, never because of anything they browsed or bought. There is no
    behavioural signal anywhere in this table and none is intended: see
    docs/decisions/0022-customer-interests.md.

    ``position`` is the order the customer put them in, which is the order
    their home page uses. A table rather than a JSON column so a deleted
    category cannot leave a dangling id behind, and so "which customers
    care about category X" stays an ordinary query.
    """

    __tablename__ = "shopping_interests"
    __table_args__ = (
        db.UniqueConstraint(
            "preferences_id", "category_id",
            name="uq_shopping_interests_preferences_category",
        ),
        db.Index("ix_shopping_interests_preferences_id", "preferences_id"),
    )

    id = db.Column(db.Integer, primary_key=True)

    preferences_id = db.Column(
        db.Integer,
        db.ForeignKey("shopping_preferences.id", ondelete="CASCADE"),
        nullable=False,
    )

    # A category the admin removes takes its interest rows with it. Nothing
    # of value is lost: the interest was a pointer at that category, and
    # the customer's other picks are untouched.
    #
    # ON DELETE CASCADE is declared for the database that enforces it, but
    # the cascade that actually runs today is the ORM one on
    # ``Category.interests``: SQLite ignores foreign-key actions unless
    # ``PRAGMA foreign_keys=ON``, and this app does not set it. Do not
    # assume a bare ondelete= does anything here.
    category_id = db.Column(
        db.Integer,
        db.ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
    )

    position = db.Column(db.Integer, nullable=False, default=0)

    preferences = db.relationship(
        "ShoppingPreferences",
        back_populates="interests",
    )

    category = db.relationship("Category", back_populates="interests")

    def __repr__(self):
        return (
            f"<ShoppingInterest prefs={self.preferences_id} "
            f"category={self.category_id}>"
        )
