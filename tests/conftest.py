"""Shared test fixtures for the Hospital Management System.

Tests use mocked database and file-system dependencies so they
can run without a MySQL server or bcrypt.
"""
from __future__ import annotations

import json
import secrets
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Generator, Optional
from unittest.mock import MagicMock, patch

import pytest

from src.constants import Role, UserStatus


# ── Sample data ────────────────────────────────────────────────

def make_user_dict(
    user_id: int = 1,
    username: str = "admin",
    role_name: str = Role.ADMIN,
    status: str = UserStatus.ACTIVE,
    password_hash: str = "",
) -> Dict[str, Any]:
    """Build a user dict as returned by UserRepository queries.

    Args:
        user_id: The user's database ID.
        username: The login username.
        role_name: The role name.
        status: Account status.
        password_hash: The bcrypt hash (empty = matches "password").

    Returns:
        A user dictionary matching the repository return format.
    """
    return {
        "user_id": user_id,
        "username": username,
        "password_hash": password_hash or _fake_hash("password"),
        "role_id": 1,
        "role_name": role_name,
        "status": status,
        "full_name": f"{username.title()} User",
        "email": f"{username}@hospital.com",
        "last_login": None,
        "failed_login_attempts": 0,
        "locked_until": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }


def _fake_hash(password: str) -> str:
    """Return a fake bcrypt-like hash for testing.

    This is NOT a real hash — it's just a deterministic string
    that the mocked ``_verify_password`` will accept.
    """
    # In real tests we mock _verify_password, so this doesn't
    # need to be a valid bcrypt string.
    return f"$2b$12$fakehash{password}"


# ── Mock repositories ──────────────────────────────────────────

@pytest.fixture
def mock_user_repo() -> MagicMock:
    """Create a mocked UserRepository with sensible defaults."""
    repo = MagicMock()
    # Default: find_by_username returns the admin user
    repo.find_by_username.return_value = make_user_dict()
    repo.find_by_id_with_role.return_value = make_user_dict()
    repo.get_role_id.return_value = 1
    repo.create_user.return_value = 99
    repo.update_login_info.return_value = None
    repo.set_locked.return_value = 1
    repo.reset_password.return_value = 1
    repo.count_active_users.return_value = 5
    return repo


@pytest.fixture
def mock_token_manager() -> Generator[MagicMock, None, None]:
    """Create a mocked RememberTokenManager in a temp directory."""
    mgr = MagicMock()
    mgr.save.return_value = None
    mgr.load.return_value = None  # No token by default
    mgr.clear.return_value = None
    mgr.exists = False
    yield mgr


@pytest.fixture
def temp_token_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for token files that auto-cleans."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def real_token_manager(temp_token_dir: Path) -> Generator[Any, None, None]:
    """Create a REAL RememberTokenManager writing to a temp dir.

    Useful for integration-style tests that want to verify file I/O.
    """
    from src.auth.remember_token import RememberTokenManager
    mgr = RememberTokenManager(storage_dir=str(temp_token_dir))
    yield mgr
    mgr.clear()


@pytest.fixture(autouse=True)
def mock_bcrypt() -> Generator[None, None, None]:
    """Mock bcrypt to avoid slow hashing in tests.

    ``_hash_password`` returns a predictable string.
    ``_verify_password`` returns True for ``"password"`` and False for anything else.
    """
    with patch("src.services.auth_service.bcrypt") as mock_bc:
        def fake_hashpw(pw: bytes, salt: bytes) -> bytes:
            return b"$2b$12$testhashedpassword123456789012345678901234567890"
        mock_bc.hashpw.side_effect = fake_hashpw
        mock_bc.gensalt.return_value = b"$2b$12$testsalt1234567890"
        mock_bc.checkpw.side_effect = lambda pw, h: pw == b"password"
        yield
