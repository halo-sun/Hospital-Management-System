"""Tests for version-agnostic MySQL service detection.

The setup wizard previously hardcoded 'mysql80' as the Windows service name,
causing it to miss other MySQL versions (MySQL91, MySQL267, etc.).  These tests
verify the new pattern-based detection logic using sc query state=all.
"""
from __future__ import annotations

import subprocess
from unittest.mock import patch, MagicMock

import pytest


# ── Sample sc query state=all output ────────────────────────────────

def _sc_output(services: list[tuple[str, str]]) -> str:
    """Build ``sc query state=all`` output from (name, state) tuples.

    Each service block in the real output looks like:

        SERVICE_NAME: MySQL267
            ...
            STATE              : 4  RUNNING
            ...
    """
    blocks = []
    for name, state in services:
        # Map human label to the numeric prefix sc uses
        state_map = {
            "RUNNING": "4  RUNNING",
            "STOPPED": "1  STOPPED",
            "PAUSED": "7  PAUSED",
        }
        state_line = state_map.get(state.upper(), f"?  {state.upper()}")
        blocks.append(
            f"SERVICE_NAME: {name}\n"
            f"        TYPE               : 10  WIN32_OWN_PROCESS\n"
            f"        STATE              : {state_line}\n"
            f"        WIN32_EXIT_CODE    : 0  (0x0)\n"
        )
    return "\n".join(blocks)


class TestEnumerateMysqlServices:
    """Tests for SetupWizardView._enumerate_mysql_services (static method)."""

    @patch("subprocess.run")
    def test_detects_mysql267_running(self, mock_run):
        """MySQL267 (the user's install) should be detected."""
        from src.gui.setup.setup_wizard_view import SetupWizardView

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=_sc_output([("MySQL267", "RUNNING")]),
            stderr="",
        )
        result = SetupWizardView._enumerate_mysql_services()
        assert result == [("MySQL267", "RUNNING")]

    @patch("subprocess.run")
    def test_detects_mysql80_running(self, mock_run):
        """MySQL80 should still be detected (backward compat)."""
        from src.gui.setup.setup_wizard_view import SetupWizardView

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=_sc_output([("MySQL80", "RUNNING")]),
            stderr="",
        )
        result = SetupWizardView._enumerate_mysql_services()
        assert result == [("MySQL80", "RUNNING")]

    @patch("subprocess.run")
    def test_detects_mariadb_running(self, mock_run):
        """MariaDB service should be detected."""
        from src.gui.setup.setup_wizard_view import SetupWizardView

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=_sc_output([("MariaDB", "RUNNING")]),
            stderr="",
        )
        result = SetupWizardView._enumerate_mysql_services()
        assert result == [("MariaDB", "RUNNING")]

    @patch("subprocess.run")
    def test_detects_stopped_service(self, mock_run):
        """A stopped MySQL267 should appear with state STOPPED."""
        from src.gui.setup.setup_wizard_view import SetupWizardView

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=_sc_output([("MySQL267", "STOPPED")]),
            stderr="",
        )
        result = SetupWizardView._enumerate_mysql_services()
        assert result == [("MySQL267", "STOPPED")]

    @patch("subprocess.run")
    def test_skips_non_mysql_services(self, mock_run):
        """Non-MySQL services should be ignored."""
        from src.gui.setup.setup_wizard_view import SetupWizardView

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=_sc_output([
                ("WSearch", "RUNNING"),
                ("MySQL267", "RUNNING"),
                ("Spooler", "STOPPED"),
            ]),
            stderr="",
        )
        result = SetupWizardView._enumerate_mysql_services()
        assert result == [("MySQL267", "RUNNING")]

    @patch("subprocess.run")
    def test_multiple_mysql_services(self, mock_run):
        """Multiple MySQL services should all be returned."""
        from src.gui.setup.setup_wizard_view import SetupWizardView

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=_sc_output([
                ("MySQL80", "STOPPED"),
                ("MySQL267", "RUNNING"),
            ]),
            stderr="",
        )
        result = SetupWizardView._enumerate_mysql_services()
        assert result == [("MySQL80", "STOPPED"), ("MySQL267", "RUNNING")]

    @patch("subprocess.run")
    def test_no_mysql_services(self, mock_run):
        """When no MySQL services exist, returns empty list."""
        from src.gui.setup.setup_wizard_view import SetupWizardView

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=_sc_output([("WSearch", "RUNNING"), ("Spooler", "STOPPED")]),
            stderr="",
        )
        result = SetupWizardView._enumerate_mysql_services()
        assert result == []

    @patch("subprocess.run")
    def test_sc_query_fails(self, mock_run):
        """Gracefully handles sc query failure."""
        from src.gui.setup.setup_wizard_view import SetupWizardView

        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        result = SetupWizardView._enumerate_mysql_services()
        assert result == []

    @patch("subprocess.run")
    def test_sc_query_not_found(self, mock_run):
        """Gracefully handles sc.exe not being available."""
        from src.gui.setup.setup_wizard_view import SetupWizardView

        mock_run.side_effect = FileNotFoundError("sc.exe not found")
        result = SetupWizardView._enumerate_mysql_services()
        assert result == []

    @patch("subprocess.run")
    def test_sc_query_timeout(self, mock_run):
        """Gracefully handles timeout."""
        from src.gui.setup.setup_wizard_view import SetupWizardView

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="sc", timeout=10)
        result = SetupWizardView._enumerate_mysql_services()
        assert result == []


class TestIsPortOpen:
    """Tests for SetupWizardView._is_port_open (static method)."""

    @patch("socket.create_connection")
    def test_port_open(self, mock_conn):
        from src.gui.setup.setup_wizard_view import SetupWizardView

        mock_conn.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)

        assert SetupWizardView._is_port_open("localhost", 3306) is True

    @patch("socket.create_connection")
    def test_port_closed(self, mock_conn):
        from src.gui.setup.setup_wizard_view import SetupWizardView

        mock_conn.side_effect = OSError("Connection refused")
        assert SetupWizardView._is_port_open("localhost", 3306) is False

    @patch("socket.create_connection")
    def test_port_timeout(self, mock_conn):
        import socket
        from src.gui.setup.setup_wizard_view import SetupWizardView

        mock_conn.side_effect = socket.timeout("timed out")
        assert SetupWizardView._is_port_open("localhost", 3306) is False
