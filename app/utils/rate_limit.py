"""Rate-limit key for authenticated endpoints.

``auth_routes.py`` keys its limits on the client IP (``get_remote_address``)
or, for account-targeted limits, the email in the request body. The
authenticated endpoints throttled after ADR 0033 want a *per-user* key —
the token identity — falling back to the IP for an anonymous or malformed
request so the limit still bites.

Flask-Limiter evaluates a decorated limit before the view's own
decorators run, so this verifies the JWT itself (optionally) rather than
relying on ``@jwt_required`` having populated the context first.
"""

from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_limiter.util import get_remote_address


def user_or_ip_key():
    identity = None
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
    except Exception:
        identity = None
    return f"user:{identity}" if identity else f"ip:{get_remote_address()}"
