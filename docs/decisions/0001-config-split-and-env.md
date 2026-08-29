# 0001 — Environment-driven configuration (CL-03, CL-04)

**Date:** 2026-08-29
**Status:** accepted
**Queue item:** 1 (blockers)

## Context

`app/config.py` had a single `Config` class with `SQLALCHEMY_DATABASE_URI`
hardcoded to `sqlite:///cedarlink.db` and `SECRET_KEY` / `JWT_SECRET_KEY`
falling back to a committed placeholder string. The frontend hardcoded
`http://localhost:5000/api` twice. The app could not run anywhere but a
developer machine, and a production deploy that forgot its `.env` would boot
silently and sign JWTs with a value visible in the repo.

## Decision

- Three config classes: `DevConfig`, `TestConfig`, `ProdConfig`, all extending
  a shared `Config` base.
- `SQLALCHEMY_DATABASE_URI` reads `DATABASE_URL` (base), `TEST_DATABASE_URL`
  (test, default `sqlite:///:memory:`), falling back to the SQLite file for
  development only.
- Selection via the `FLASK_CONFIG` env var (`development` | `testing` |
  `production`); defaults to `development`. `create_app(config_object=None)`
  also accepts an explicit class for tests.
- `Config.validate()` is a no-op hook. `ProdConfig.validate()` raises
  `RuntimeError` if `SECRET_KEY`, `JWT_SECRET_KEY`, or
  `TWO_FACTOR_ENCRYPTION_KEY` is unset. `get_config()` calls `validate()`
  before returning, so a misconfigured production process fails at startup.
- The placeholder secret fallback now lives only in `DevConfig` / `TestConfig`.
- Frontend: one `API_BASE_URL` constant from `import.meta.env.VITE_API_URL`,
  no hardcoded host. `frontend/.env.example` documents the variable; a local
  `frontend/.env` (gitignored) supplies it in development.

## Consequences

- A fresh clone needs `frontend/.env` (copy from `.env.example`); the README
  will state this.
- `ProdConfig` guard fires at config resolution (app startup), not at module
  import of `app.config`, so importing the config module in development stays
  safe.
- Behaviour in development is unchanged: same SQLite file, same placeholder
  secrets when `.env` is absent.
