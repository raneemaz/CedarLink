"""One error shape for the whole API (CL-20).

Every error response is ``{"error": <message>}``. Unexpected failures add a
``correlation_id`` that also lands in the logs — and nothing else. No
exception text, table names or constraint names ever reach the client.
"""

import uuid

from flask import current_app, jsonify
from werkzeug.exceptions import HTTPException

GENERIC_500_MESSAGE = "An unexpected error occurred. Please try again."


def _json_error(message, status, **extra):
    return jsonify({"error": message, **extra}), status


def log_and_correlate(exc, context):
    """Log ``exc`` with a fresh correlation id and return the id.

    The id is safe to hand to the client; the stack trace stays in the log.
    """
    correlation_id = uuid.uuid4().hex[:12]
    current_app.logger.exception(
        "%s [correlation_id=%s]", context, correlation_id
    )
    return correlation_id


def internal_error(exc, context):
    """A ready-made 500 response for a view that caught its own exception."""
    correlation_id = log_and_correlate(exc, context)
    return _json_error(
        GENERIC_500_MESSAGE, 500, correlation_id=correlation_id
    )


def register_error_handlers(app):
    """Blueprint-agnostic handlers for 400/401/403/404/405/422/500."""

    @app.errorhandler(HTTPException)
    def _http_exception(exc):
        # Routing / method-not-allowed / abort() errors: JSON, not the
        # default Werkzeug HTML page. Explicit `return ..., 4xx` responses
        # in views are unaffected — they are not exceptions.
        return _json_error(exc.description, exc.code)

    @app.errorhandler(Exception)
    def _unhandled(exc):
        # In production this is the catch-all. Under TESTING Flask re-raises
        # instead, so views that must return a 500 in tests catch their own
        # exception and call internal_error().
        if isinstance(exc, HTTPException):
            return _json_error(exc.description, exc.code)

        from app.extensions import db

        db.session.rollback()
        correlation_id = log_and_correlate(exc, "unhandled exception")
        return _json_error(
            GENERIC_500_MESSAGE, 500, correlation_id=correlation_id
        )
