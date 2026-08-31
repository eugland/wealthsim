"""Tests for token storage: keyring-preferred with plaintext-file fallback. No real keyring."""

from __future__ import annotations

from typing import Any

from wealthsim import _store


class _FakeKeyring:
    """Minimal in-memory stand-in for the keyring module."""

    def __init__(self) -> None:
        self._data: dict[tuple[str, str], str] = {}

    def set_password(self, service: str, account: str, value: str) -> None:
        self._data[(service, account)] = value

    def get_password(self, service: str, account: str) -> str | None:
        return self._data.get((service, account))

    def delete_password(self, service: str, account: str) -> None:
        del self._data[(service, account)]


def test_keyring_roundtrip_no_file(tmp_path: Any, monkeypatch: Any) -> None:
    fake = _FakeKeyring()
    monkeypatch.setattr(_store, "_keyring", lambda: fake)
    cache = tmp_path / ".env"

    backend = _store.save_tokens({"access_token": "abc"}, cache_path=str(cache))
    assert backend == "keyring"
    assert not cache.exists()  # nothing written to disk
    assert _store.load_tokens(cache_path=str(cache)) == {"access_token": "abc"}


def test_file_fallback_when_no_keyring(tmp_path: Any, monkeypatch: Any) -> None:
    monkeypatch.setattr(_store, "_keyring", lambda: None)
    cache = tmp_path / ".env"

    backend = _store.save_tokens({"access_token": "xyz"}, cache_path=str(cache))
    assert backend == "file"
    assert cache.exists()
    assert _store.load_tokens(cache_path=str(cache)) == {"access_token": "xyz"}


def test_use_keyring_false_forces_file(tmp_path: Any, monkeypatch: Any) -> None:
    monkeypatch.setattr(_store, "_keyring", lambda: _FakeKeyring())
    cache = tmp_path / ".env"
    assert _store.save_tokens({"a": "1"}, cache_path=str(cache), use_keyring=False) == "file"
    assert cache.exists()


def test_load_missing_raises(tmp_path: Any, monkeypatch: Any) -> None:
    monkeypatch.setattr(_store, "_keyring", lambda: None)
    try:
        _store.load_tokens(cache_path=str(tmp_path / "nope.env"))
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("expected FileNotFoundError")
