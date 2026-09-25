"""Idempotency-key support for actions that must not run twice.

Used by ``POST /orders`` (checkout) so that a double-click on "Place
order", or a client retry after a network timeout, replays the first
attempt's response instead of placing a second order / taking a second
payment. See ``app.models.idempotency_key.IdempotencyKey`` for the storage
model and ``docs/decisions`` for the design rationale.

Usage in a route::

    key = request.headers.get("Idempotency-Key")
    if key:
        try:
            cached = begin(user_id, "checkout", key)
        except IdempotencyInProgress:
            return jsonify({"error": "..."}), 409
        if cached is not None:
            status_code, body = cached
            return jsonify(body), status_code

    try:
        result = do_the_thing()
    except SomeError:
        if key:
            fail(user_id, "checkout", key)
        raise

    if key:
        finish(user_id, "checkout", key, 201, result)
    return jsonify(result), 201

A missing ``Idempotency-Key`` header is accepted and simply skips all of
this -- the route behaves exactly as it did before the key existed. This
keeps existing callers (and tests) working; only clients that send a key
get the replay guarantee.
"""

import json

from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.idempotency_key import IdempotencyKey


class IdempotencyInProgress(Exception):
    """Another request is already running with this exact key right now."""


def begin(user_id, scope, key):
    """Claim ``key`` for ``(user_id, scope)``.

    Returns ``(status_code, body)`` to replay verbatim when this exact
    request already completed once. Returns ``None`` when the caller now
    owns the key and should go ahead and perform the action, then call
    :func:`finish` or :func:`fail`. Raises :class:`IdempotencyInProgress`
    when a concurrent request (same key) is still in flight.
    """
    existing = IdempotencyKey.query.filter_by(
        user_id=user_id, scope=scope, key=key
    ).first()

    if existing is not None:
        if existing.status == "completed":
            return existing.response_status, json.loads(
                existing.response_body
            )

        if existing.status == "in_progress":
            raise IdempotencyInProgress()

        # status == "failed": the earlier attempt never produced a
        # result (the action raised), so this call is free to try again
        # as if the key were unused.
        db.session.delete(existing)
        db.session.commit()

    db.session.add(IdempotencyKey(
        user_id=user_id, scope=scope, key=key, status="in_progress"
    ))

    try:
        db.session.commit()
    except IntegrityError:
        # Lost the race to a concurrent request carrying the same key.
        db.session.rollback()
        raise IdempotencyInProgress()

    return None


def finish(user_id, scope, key, status_code, body):
    """Cache the response a freshly-completed action produced."""
    IdempotencyKey.query.filter_by(
        user_id=user_id, scope=scope, key=key
    ).update({
        "status": "completed",
        "response_status": status_code,
        "response_body": json.dumps(body),
    })
    db.session.commit()


def fail(user_id, scope, key):
    """Release a key whose action raised, so a retry can start clean."""
    IdempotencyKey.query.filter_by(
        user_id=user_id, scope=scope, key=key
    ).update({"status": "failed"})
    db.session.commit()
