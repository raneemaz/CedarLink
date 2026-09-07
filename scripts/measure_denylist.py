"""token_denylist lookup cost vs table size (ADR 0033 §5 item 6 / ADR 0032).

The JWT blocklist loader runs `SELECT id FROM token_denylist WHERE jti = ?`
on every authenticated request. `jti` is UNIQUE + indexed, so this should
be O(log n) — but S-2 never measured it, and there is no cleanup job, so
the table only grows.

This builds a throwaway database at migration head, times an authenticated
request (`GET /api/orders`, which hits the loader) with the table empty
and then with 100,000 expired rows, and reports the per-request delta.

    python scripts/measure_denylist.py
"""

import statistics
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flask_jwt_extended import create_access_token  # noqa: E402
from sqlalchemy import insert, text  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

from app import create_app  # noqa: E402
from app.config import TestConfig  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models.token_denylist import TokenDenylist  # noqa: E402
from app.models.user import User  # noqa: E402

ROWS = 100_000
SAMPLES = 400


def _median_ms(client, headers):
    times = []
    for _ in range(SAMPLES):
        start = time.perf_counter()
        client.get("/api/orders", headers=headers)
        times.append((time.perf_counter() - start) * 1000)
    return statistics.median(times), statistics.quantiles(times, n=100)[98]


def main():
    db_path = Path(__file__).resolve().parents[1] / "_denylist.db"
    db_path.unlink(missing_ok=True)

    class Cfg(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path.as_posix()}"
        RATELIMIT_ENABLED = False

    app = create_app(Cfg)
    ctx = app.app_context()
    ctx.push()
    db.create_all()

    user = User(
        first_name="D", last_name="L", email="denylist@probe.local",
        password=generate_password_hash("x", method="pbkdf2:sha256:1"),
        phone="+9611", role="customer", is_verified=True,
        verification_method="email",
    )
    db.session.add(user)
    db.session.commit()
    headers = {
        "Authorization": "Bearer " + create_access_token(
            identity=str(user.id), additional_claims={"role": "customer"}
        )
    }
    client = app.test_client()

    empty_med, empty_p99 = _median_ms(client, headers)

    expired = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        days=40
    )
    created = expired - timedelta(minutes=15)
    batch = []
    for i in range(ROWS):
        batch.append({
            "jti": uuid.uuid4().hex, "token_type": "access",
            "user_id": user.id, "created_at": created, "expires_at": expired,
        })
        if len(batch) == 5000:
            db.session.execute(insert(TokenDenylist.__table__), batch)
            batch.clear()
    if batch:
        db.session.execute(insert(TokenDenylist.__table__), batch)
    db.session.commit()
    db.session.execute(text("ANALYZE"))
    db.session.commit()

    full_med, full_p99 = _median_ms(client, headers)

    plan = " | ".join(
        r[-1] for r in db.session.execute(text(
            "EXPLAIN QUERY PLAN "
            "SELECT id FROM token_denylist WHERE jti = 'x'"
        ))
    )

    engine = db.engine
    ctx.pop()
    engine.dispose()
    db_path.unlink(missing_ok=True)

    report = f"""# token_denylist growth cost (scripts/measure_denylist.py)

`GET /api/orders` (hits the JWT blocklist loader), median of {SAMPLES}
requests, in-process test client.

| token_denylist rows | median ms | p99 ms |
|--:|--:|--:|
| 0 | {empty_med:.3f} | {empty_p99:.3f} |
| {ROWS:,} (all expired) | {full_med:.3f} | {full_p99:.3f} |

Per-request delta at {ROWS:,} rows: **{full_med - empty_med:+.3f} ms** median.

Plan for the lookup:

```
{plan}
```
"""
    print(report)
    dest = Path(__file__).resolve().parents[1] / "docs" / "decisions" / \
        "_denylist-measurements.md"
    dest.write_text(report, encoding="utf-8")
    print(f"written to {dest}")


if __name__ == "__main__":
    main()
