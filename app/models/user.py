from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    first_name = db.Column(db.String(50), nullable=False)

    last_name = db.Column(db.String(50), nullable=False)

    email = db.Column(db.String(120), unique=True, nullable=False)

    password = db.Column(db.String(255), nullable=False)

    phone = db.Column(db.String(20), nullable=True)

    language = db.Column(
        db.Enum("en", "ar", "fr"),
        nullable=False,
        default="en",
        server_default="en",
    )

    currency = db.Column(
        db.Enum("USD", "LBP"),
        nullable=False,
        default="USD",
        server_default="USD",
    )

    # Light, dark, or follow the device. Stored on the account rather than
    # in the browser so it travels between a customer's phone and their
    # laptop, the same way language and currency already do. "system" is
    # the default because it is the only value that is right without the
    # user having said anything.
    theme = db.Column(
        db.Enum("light", "dark", "system", name="theme_preference"),
        nullable=False,
        default="system",
        server_default="system",
    )

    role = db.Column(db.Enum("customer", "vendor", "admin"), nullable=False)

    is_verified = db.Column(db.Boolean, nullable=False, default=False)

    verification_method = db.Column(db.String(20), nullable=True)

    two_factor_enabled = db.Column(db.Boolean, nullable=False, default=False)

    two_factor_method = db.Column(db.String(20), nullable=True)

    two_factor_totp_secret = db.Column(db.Text, nullable=True)

    # Highest TOTP time step this user has already authenticated with.
    # RFC 6238 s5.2 requires a code be accepted at most once, and pyotp
    # is stateless, so the high-water mark lives here.
    two_factor_last_totp_counter = db.Column(db.Integer, nullable=True)

    # User-controlled self-deactivation. The user can clear this via
    # POST /auth/reactivate.
    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=db.true(),
    )

    deleted_at = db.Column(db.DateTime, nullable=True)

    # Admin-controlled. Kept separate from is_active on purpose: a suspended
    # user must not be able to lift their own suspension via /auth/reactivate.
    suspended_at = db.Column(db.DateTime, nullable=True)
    suspension_reason = db.Column(db.String(255), nullable=True)

    # Bulk JWT revocation (CL-09): any access/refresh token issued before
    # this instant is rejected. Set on password reset, admin suspension and
    # self-deactivation. Naive UTC, to match the token `iat` comparison.
    tokens_revoked_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, server_default=db.func.now())

    updated_at = db.Column(
        db.DateTime, server_default=db.func.now(), onupdate=db.func.now()
    )

    cart = db.relationship(
        "Cart",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    notification_preferences = db.relationship(
        "NotificationPreferences",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    shopping_preferences = db.relationship(
        "ShoppingPreferences",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    notifications = db.relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="Notification.created_at.desc()",
    )

    stores = db.relationship(
        "Store", back_populates="owner", cascade="all, delete-orphan"
    )

    orders = db.relationship(
        "Order", back_populates="user", cascade="all, delete-orphan"
    )

    reviews = db.relationship(
        "Review", back_populates="user", cascade="all, delete-orphan"
    )

    addresses = db.relationship(
        "Address", back_populates="user", cascade="all, delete-orphan"
    )

    payment_methods = db.relationship(
        "PaymentMethod", back_populates="user", cascade="all, delete-orphan"
    )

    two_factor_challenges = db.relationship(
        "TwoFactorChallenge",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    two_factor_recovery_codes = db.relationship(
        "TwoFactorRecoveryCode",
        back_populates="user",
        cascade="all, delete-orphan",
    )
