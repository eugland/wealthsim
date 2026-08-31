"""Token storage. Prefers the OS keyring (Credential Manager / Keychain / libsecret);
falls back to a plaintext JSON file only when keyring is unavailable or disabled.

The captured token dict is stored as one JSON blob so access_token, refresh_token, and
device_id travel together.
"""

from __future__ import annotations

import json
import warnings
from typing import Any, Optional

SERVICE = "wealthsim"
ACCOUNT = "session"


def _keyring() -> Any:
    """Return the keyring module, or None if it isn't installed/usable."""
    try:
        import keyring

        return keyring
    except Exception:
        return None


def save_tokens(
    tokens: dict[str, str],
    cache_path: Optional[str] = ".env",
    use_keyring: bool = True,
) -> str:
    """Persist ``tokens``. Returns the backend used: ``"keyring"`` or ``"file"``.

    With ``use_keyring`` (default) and keyring available, tokens go to the OS secret
    store and NOTHING is written to disk. Otherwise they fall back to ``cache_path``
    as plaintext JSON (with a warning), if a path is given.
    """
    if use_keyring:
        kr = _keyring()
        if kr is not None:
            kr.set_password(SERVICE, ACCOUNT, json.dumps(tokens))
            return "keyring"
        warnings.warn(
            "keyring unavailable — falling back to plaintext token storage. "
            "Install `keyring` for OS-backed secure storage.",
            stacklevel=2,
        )
    if not cache_path:
        raise ValueError("No keyring backend and no cache_path — nowhere to store tokens.")
    with open(cache_path, "w") as f:
        json.dump(tokens, f, indent=2)
    return "file"


def load_tokens(
    cache_path: Optional[str] = ".env",
    use_keyring: bool = True,
) -> dict[str, str]:
    """Load tokens, trying the keyring first (if enabled), then ``cache_path``.

    Raises ``FileNotFoundError`` if neither backend has anything stored.
    """
    if use_keyring:
        kr = _keyring()
        if kr is not None:
            blob = kr.get_password(SERVICE, ACCOUNT)
            if blob:
                return json.loads(blob)
    if cache_path:
        try:
            with open(cache_path) as f:
                return json.load(f)
        except FileNotFoundError:
            pass
    raise FileNotFoundError("No cached tokens found (checked keyring and cache_path).")


def clear_tokens(cache_path: Optional[str] = ".env", use_keyring: bool = True) -> None:
    """Delete stored tokens from both backends where present."""
    if use_keyring:
        kr = _keyring()
        if kr is not None:
            try:
                kr.delete_password(SERVICE, ACCOUNT)
            except Exception:
                pass
    if cache_path:
        import os

        try:
            os.remove(cache_path)
        except FileNotFoundError:
            pass
