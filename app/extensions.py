from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

# Auth-endpoint throttling (CL-10). In-memory storage is per-process — fine
# for a single gunicorn worker; production with several workers should set
# RATELIMIT_STORAGE_URI to a shared Redis.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
    headers_enabled=True,
)
