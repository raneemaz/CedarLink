# token_denylist growth cost (scripts/measure_denylist.py)

`GET /api/orders` (hits the JWT blocklist loader), median of 400
requests, in-process test client.

| token_denylist rows | median ms | p99 ms |
|--:|--:|--:|
| 0 | 1.501 | 4.434 |
| 100,000 (all expired) | 1.484 | 4.475 |

Per-request delta at 100,000 rows: **-0.016 ms** median.

Plan for the lookup:

```
SEARCH token_denylist USING COVERING INDEX ix_token_denylist_jti (jti=?)
```
