import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-to-a-long-secret-key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY",
                               "change-this-to-a-long-secret-key")

    JWT_ACCESS_TOKEN_EXPIRES = 15 * 60  # 15 minutes
    JWT_REFRESH_TOKEN_EXPIRES = 30 * 24 * 60 * 60

    TWO_FACTOR_CHALLENGE_TTL_SECONDS = int(
        os.getenv("TWO_FACTOR_CHALLENGE_TTL_SECONDS", "600")
    )
    TWO_FACTOR_MAX_ATTEMPTS = int(
        os.getenv("TWO_FACTOR_MAX_ATTEMPTS", "5")
    )
    TWO_FACTOR_MAX_EMAIL_SENDS = int(
        os.getenv("TWO_FACTOR_MAX_EMAIL_SENDS", "3")
    )
    TWO_FACTOR_EMAIL_RESEND_COOLDOWN_SECONDS = int(
        os.getenv("TWO_FACTOR_EMAIL_RESEND_COOLDOWN_SECONDS", "60")
    )
    TWO_FACTOR_ISSUER = os.getenv("TWO_FACTOR_ISSUER", "CedarLink")
    TWO_FACTOR_ENCRYPTION_KEY = os.getenv("TWO_FACTOR_ENCRYPTION_KEY")

    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_FROM = os.getenv("MAIL_FROM")
    MAIL_SUPPRESS_SEND = os.getenv(
        "MAIL_SUPPRESS_SEND",
        "false"
    ).lower() == "true"

    SQLALCHEMY_DATABASE_URI = "sqlite:///cedarlink.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Currency preference / display conversion.
    # Base currency is the currency every stored price, cart total, order
    # total and payment amount is expressed in. Conversion is display-only.
    BASE_CURRENCY = "USD"
    SUPPORTED_CURRENCIES = ["USD", "LBP"]
    EXCHANGE_RATE_API_URL = os.getenv(
        "EXCHANGE_RATE_API_URL",
        "https://open.er-api.com/v6/latest/USD",
    )
    EXCHANGE_RATE_TTL_SECONDS = int(
        os.getenv("EXCHANGE_RATE_TTL_SECONDS", "21600")  # 6 hours
    )
    # Used only when no successful API fetch has ever happened this process.
    EXCHANGE_RATE_FALLBACK = {
        "USD": 1.0,
        "LBP": float(os.getenv("EXCHANGE_RATE_FALLBACK_LBP", "89000")),
    }

    UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, "uploads", "products")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
    ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
    MAX_IMAGES_PER_PRODUCT = 5
