"""JWT revocation (CL-09).

Two mechanisms, one blocklist check:

* **Logout** revokes one token — its ``jti`` goes in ``token_denylist``.
* **Password reset / admin suspension / self-deactivation** revoke every
  token a user holds. Enumerating outstanding tokens is impossible, so
  instead ``User.tokens_revoked_at`` is stamped and any token issued before
  that instant is rejected.

The blocklist loader runs on every ``@jwt_required`` request, so a
suspended user's live token stops working on their very next call, not
when it expires.
"""

from datetime import datetime, timezone

from app.extensions import db
from app.models.token_denylist import TokenDenylist
from app.models.user import User


def _naive_utc(moment=None):
    moment = moment or datetime.now(timezone.utc)
    return moment.astimezone(timezone.utc).replace(tzinfo=None)


def _from_timestamp(seconds):
    return datetime.fromtimestamp(seconds, tz=timezone.utc).replace(tzinfo=None)


def register_jwt_callbacks(jwt):
    @jwt.token_in_blocklist_loader
    def _token_is_revoked(_jwt_header, jwt_payload):
        jti = jwt_payload.get("jti")
        if jti is not None:
            revoked = db.session.query(
                TokenDenylist.id
            ).filter_by(jti=jti).first()
            if revoked is not None:
                return True

        return _issued_before_bulk_revocation(jwt_payload)


def _issued_before_bulk_revocation(jwt_payload):
    identity = jwt_payload.get("sub")
    if identity is None:
        return False

    user = db.session.get(User, int(identity))
    if user is None or user.tokens_revoked_at is None:
        return False

    issued_at = jwt_payload.get("iat")
    if issued_at is None:
        return True

    return _from_timestamp(issued_at) < user.tokens_revoked_at


def revoke_current_token(jwt_payload):
    """Deny-list the token the current request authenticated with."""
    db.session.add(
        TokenDenylist(
            jti=jwt_payload["jti"],
            token_type=jwt_payload.get("type", "access"),
            user_id=int(jwt_payload["sub"]),
            expires_at=_from_timestamp(jwt_payload["exp"]),
        )
    )
    db.session.commit()


def revoke_refresh_token(token_string):
    """Deny-list a refresh token given as a raw string (logout). Best-effort."""
    from flask_jwt_extended import decode_token

    try:
        payload = decode_token(token_string)
    except Exception:
        return

    if payload.get("type") != "refresh" or "jti" not in payload:
        return

    revoke_current_token(payload)


def revoke_all_tokens(user):
    """Invalidate every token this user currently holds.

    Sets the cutoff; the caller commits alongside its own changes.
    """
    user.tokens_revoked_at = _naive_utc()
