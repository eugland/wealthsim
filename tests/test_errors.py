"""Tests for the exception taxonomy."""

from __future__ import annotations

import wealthsim
from wealthsim.client import LoginFailed, OTPRequired, WSError


def test_hierarchy() -> None:
    # LoginFailed and OTPRequired are both WSError subclasses (catchable via base).
    assert issubclass(LoginFailed, WSError)
    assert issubclass(OTPRequired, WSError)


def test_wserror_carries_response() -> None:
    err = WSError("boom", response={"error": "x"})
    assert err.response == {"error": "x"}
    assert str(err) == "boom"


def test_wserror_response_defaults_none() -> None:
    # Existing single-arg raises keep working.
    assert WSError("just a message").response is None


def test_login_failed_is_exported() -> None:
    assert wealthsim.LoginFailed is LoginFailed
