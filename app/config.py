import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))

# Used as a stand-in secret in development and testing only. ProdConfig
# refuses to start if the real values are not supplied by the environment.
_PLACEHOLDER_SECRET = "change-this-to-a-long-secret-key"
# A syntactically valid Fernet key so the 2FA service can import under tests
# without a real key being configured.
_PLACEHOLDER_FERNET_KEY = "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="


class Config:
    # Secrets have no usable default at this level. DevConfig / TestConfig
    # supply placeholders; ProdConfig requires the environment to set them.
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

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

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///cedarlink.db",
    )
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

    @classmethod
    def validate(cls):
        """Hook for environment-specific config guards. No-op by default."""


class DevConfig(Config):
    DEBUG = True

    SECRET_KEY = os.getenv("SECRET_KEY", _PLACEHOLDER_SECRET)
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", _PLACEHOLDER_SECRET)


class TestConfig(Config):
    TESTING = True

    # File-based, not sqlite:///:memory: — an in-memory URL gives every
    # connection its own empty database, which makes pytest fail
    # intermittently with "no such table".
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URL",
        "sqlite:///" + os.path.join(PROJECT_ROOT, "test.db"),
    )

    SECRET_KEY = os.getenv("SECRET_KEY", _PLACEHOLDER_SECRET)
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", _PLACEHOLDER_SECRET)
    TWO_FACTOR_ENCRYPTION_KEY = os.getenv(
        "TWO_FACTOR_ENCRYPTION_KEY",
        _PLACEHOLDER_FERNET_KEY,
    )
    MAIL_SUPPRESS_SEND = True

    # The limiter is fully installed under tests so its behaviour is
    # exercised, but conftest resets its storage after every test so counts
    # never leak between them. Individual tests stay well under the limits;
    # the throttling tests deliberately blow past them.
    RATELIMIT_ENABLED = True


class ProdConfig(Config):
    DEBUG = False

    # Secrets that must never fall back to a committed placeholder.
    REQUIRED_ENV = (
        "SECRET_KEY",
        "JWT_SECRET_KEY",
        "TWO_FACTOR_ENCRYPTION_KEY",
    )

    @classmethod
    def validate(cls):
        missing = [name for name in cls.REQUIRED_ENV if not os.getenv(name)]
        if missing:
            raise RuntimeError(
                "ProdConfig requires these environment variables to be set: "
                + ", ".join(missing)
            )


_CONFIGS = {
    "development": DevConfig,
    "testing": TestConfig,
    "production": ProdConfig,
}


def get_config(name=None):
    """Resolve a config class from an explicit name or FLASK_CONFIG.

    Defaults to development. The selected class is validated before it is
    returned, so a production process with missing secrets fails at startup
    rather than serving requests signed with a placeholder key.
    """
    name = (name or os.getenv("FLASK_CONFIG") or "development").lower()
    config_class = _CONFIGS.get(name, DevConfig)
    config_class.validate()
    return config_class
