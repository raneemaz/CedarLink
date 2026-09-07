"""app.utils.db_retry.with_write_retry — retries a 'database is locked'
error, nothing else. ADR 0033 §5 item 7 / ADR 0032 §3.
"""

import pytest
from sqlalchemy.exc import OperationalError

from app.utils.db_retry import is_locked_error, with_write_retry


def _locked():
    return OperationalError("stmt", {}, Exception("database is locked"))


def _other():
    return OperationalError("stmt", {}, Exception("no such column: x"))


def test_is_locked_error_only_matches_the_lock_message():
    assert is_locked_error(_locked())
    assert not is_locked_error(_other())
    assert not is_locked_error(ValueError("nope"))


def test_it_succeeds_after_a_transient_lock(app):
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise _locked()
        return "ok"

    with app.app_context():
        assert with_write_retry(flaky, base_delay=0) == "ok"
    assert calls["n"] == 3


def test_it_gives_up_after_the_attempt_budget(app):
    calls = {"n": 0}

    def always_locked():
        calls["n"] += 1
        raise _locked()

    with app.app_context():
        with pytest.raises(OperationalError):
            with_write_retry(always_locked, attempts=3, base_delay=0)
    assert calls["n"] == 3


def test_a_non_lock_error_is_not_retried(app):
    calls = {"n": 0}

    def broken():
        calls["n"] += 1
        raise _other()

    with app.app_context():
        with pytest.raises(OperationalError):
            with_write_retry(broken, base_delay=0)
    assert calls["n"] == 1
