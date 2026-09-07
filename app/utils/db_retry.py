"""A tiny retry for the one write path that measurably needs it: checkout.

Under a burst of concurrent checkouts, SQLite's single writer means a few
transactions wait past the 5 s busy timeout and raise
``sqlite3.OperationalError: database is locked`` — ADR 0032 §3 measured
0–5 of 100 at N≈100. The transaction has fully rolled back at that point,
so re-running it from scratch is safe. Two short retries turn most of
those failures into a slightly slower success.

Deliberately not a general decorator: only checkout uses it. A read path
does not need it (readers do not block readers), and a broad retry would
paper over genuine contention elsewhere.
"""

import time

from sqlalchemy.exc import OperationalError

from app.extensions import db

_LOCKED = ("database is locked", "database table is locked")


def is_locked_error(exc):
    return isinstance(exc, OperationalError) and any(
        marker in str(getattr(exc, "orig", exc)).lower() for marker in _LOCKED
    )


def with_write_retry(fn, *, attempts=3, base_delay=0.05):
    """Run ``fn``; on a 'database is locked' error roll back, back off a
    little, and try again — up to ``attempts`` times total. Any other
    error, or the last attempt, propagates unchanged."""
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except OperationalError as exc:
            if attempt == attempts or not is_locked_error(exc):
                raise
            db.session.rollback()
            time.sleep(base_delay * attempt)
