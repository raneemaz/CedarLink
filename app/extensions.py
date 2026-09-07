import sqlite3

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()


@event.listens_for(Engine, "connect")
def _enforce_sqlite_foreign_keys(dbapi_connection, connection_record):
    """Turn foreign keys on for every SQLite connection, in every config.

    SQLite parses FOREIGN KEY clauses but ignores them unless
    ``PRAGMA foreign_keys=ON`` is issued per connection. Registered on the
    ``Engine`` class so it covers the app engine, migrations, and anything
    a test opens. Guarded on the driver so a non-SQLite backend is
    untouched. Until ADR 0033 this ran only under the test suite
    (``conftest.py``); it is now on everywhere. See
    docs/decisions/0023-foreign-key-enforcement.md and 0033-security-pass.md.
    """
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# Auth-endpoint throttling (CL-10). In-memory storage is per-process — fine
# for a single gunicorn worker; production with several workers should set
# RATELIMIT_STORAGE_URI to a shared Redis.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
    headers_enabled=True,
)
