from app.extensions import db


class OrderItem(db.Model):
    __tablename__ = "order_items"
    __table_args__ = (
        db.Index("ix_order_items_product_id", "product_id"),
        # The dashboard's goods/units figures JOIN order_items to orders;
        # without this the join scans all order_items (ADR 0032 F1).
        db.Index("ix_order_items_order_id", "order_id"),
        db.Index("ix_order_items_variant_id", "variant_id"),
    )

    id = db.Column(db.Integer, primary_key=True)

    order_id = db.Column(
        db.Integer,
        db.ForeignKey("orders.id"),
        nullable=False
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id"),
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        nullable=False
    )

    unit_price = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    # Null means the plain product was ordered. When set, the variant may
    # later be renamed or retired, so its label is denormalised here at
    # order time — the customer's history must still read "Red, Medium".
    # (ADR 0035; the sibling product_name_* denormalisation the plan
    # assumed does not actually exist yet — see the ADR.)
    variant_id = db.Column(
        db.Integer,
        db.ForeignKey("product_variants.id"),
        nullable=True
    )

    variant_label_en = db.Column(db.String(255), nullable=True)
    variant_label_ar = db.Column(db.String(255), nullable=True)
    variant_label_fr = db.Column(db.String(255), nullable=True)

    order = db.relationship(
        "Order",
        back_populates="items"
    )

    product = db.relationship(
        "Product",
        back_populates="order_items"
    )

    variant = db.relationship("ProductVariant")
