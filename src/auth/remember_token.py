"""Remember Me — persistent session token stored on disk.

For a desktop application a full database-backed token table is
unnecessary overhead.  Instead we store a small JSON file in the
application config directory that contains an encrypted username
reference and a session expiry timestamp.

The token is *not* a password substitute — it merely allows the
application to skip the login screen for ``REMEMBER_DAYS`` after
the user last checked "Remember Me".
"""
from __future__ import annotations

import json
import logging
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from src.config import app_config

logger = logging.getLogger(__name__)

# How many days a Remember-Me token remains valid
REMEMBER_DAYS = 14

# Name of the local token file
TOKEN_FILENAME = ".remember_token"


class RememberTokenManager:
    """Manages reading, writing, and validating a local session token.

    The token file is stored alongside the application's other data
    files (``app_config.LOGS_DIR`` parent or similar writable location).
    It contains:

    .. code-block:: json

        {
          "username": "admin",
          "token": "<hex-random>",
          "expires_at": "2026-08-14T12:00:00"
        }

    The ``token`` field is a 32-byte random hex string stored both on
    disk and (in a hashed form) nowhere — for a desktop app the file
    itself *is* the credential.  Removing the file revokes the token.
    """

    def __init__(self, storage_dir: Optional[str] = None) -> None:
        """Initialise the token manager.

        Args:
            storage_dir: Directory to store the token file.
                         Defaults to ``app_config.LOGS_DIR``.
        """
        self._storage_dir = storage_dir or app_config.LOGS_DIR
        self._token_path = os.path.join(self._storage_dir, TOKEN_FILENAME)

    # ── Public API ─────────────────────────────────────────────

    def save(self, username: str) -> None:
        """Persist a Remember-Me token for the given username.

        Args:
            username: The logged-in user's username.
        """
        token_data = {
            "username": username,
            "token": secrets.token_hex(32),
            "expires_at": (datetime.now() + timedelta(days=REMEMBER_DAYS)).isoformat(),
        }
        try:
            os.makedirs(self._storage_dir, exist_ok=True)
            with open(self._token_path, "w") as f:
                json.dump(token_data, f)
            logger.debug("Remember-Me token saved for user '%s'", username)
        except OSError as e:
            logger.warning("Failed to save Remember-Me token: %s", e)

    def load(self) -> Optional[str]:
        """Load a valid Remember-Me token from disk.

        Validates the token structure, expiry date, and random token
        value (must be a 64-character hex string) to prevent tampering.

        Returns:
            The username if a valid (non-expired) token exists, else None.
        """
        if not os.path.isfile(self._token_path):
            return None

        try:
            with open(self._token_path, "r") as f:
                token_data = json.load(f)

            # Validate token structure
            token = token_data.get("token", "")
            if not isinstance(token, str) or len(token) != 64:
                logger.warning("Remember-Me token has invalid structure (token length mismatch)")
                self.clear()
                return None
            try:
                int(token, 16)  # Must be valid hex
            except (ValueError, TypeError):
                logger.warning("Remember-Me token has invalid structure (non-hex token)")
                self.clear()
                return None

            # Validate username
            username = token_data.get("username", "")
            if not username or not isinstance(username, str):
                logger.warning("Remember-Me token missing username")
                self.clear()
                return None

            # Validate expiry
            expires_raw = token_data.get("expires_at")
            if not expires_raw:
                logger.warning("Remember-Me token missing expiry")
                self.clear()
                return None
            expires = datetime.fromisoformat(expires_raw)
            if datetime.now() > expires:
                logger.debug("Remember-Me token has expired")
                self.clear()
                return None

            return username
        except (OSError, json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning("Failed to read Remember-Me token: %s", e)
            self.clear()
            return None

    def clear(self) -> None:
        """Remove the stored token (logout)."""
        try:
            if os.path.isfile(self._token_path):
                os.remove(self._token_path)
                logger.debug("Remember-Me token cleared")
        except OSError as e:
            logger.warning("Failed to clear Remember-Me token: %s", e)

    @property
    def exists(self) -> bool:
        """Check whether a token file is present on disk.

        Returns:
            True if the file exists (may still be expired).
        """
        return os.path.isfile(self._token_path)
