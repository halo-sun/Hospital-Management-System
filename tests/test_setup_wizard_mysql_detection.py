"""Tests for version-agnostic MySQL service detection.

The setup wizard previously hardcoded 'mysql80' as the Windows service name,
causing it to miss other MySQL versions (MySQL91, MySQL267, etc.).  These tests
verify the new pattern-based detection logic.
"""
from __future__ import annotations

import subprocess
from unittest.mock import patch, MagicMock

import pytest


class TestFindMysqlService:
    """Tests for SetupWizardView._find_mysql_service (static method)."""

    POWERSHELL_CMD = [
        "powershell", "-NoProfile", "-Command",
        "Get-Service | Where-Object { $_.Name -match '^(MySQL|MariaDB)' }"
        " | Select-Object Name, Status, DisplayName | Format-List",
    ]

    def _make_output(self, services: list[tuple[str, str, str]]) -> str:
        """Build Format-List output from (Name, Status, DisplayName) tuples."""
        blocks = []
        for name, status, display in services:
            blocks.append(f"Name           : {name}")
            blocks.append(f"Status         : {status}")
            blocks.append(f"DisplayName    : {display}")
        return "\n".join(blocks)

    @patch("subprocess.run")
    def test_detects_mysql267_running(self, mock_run):
        """MySQL267 (the user's install) should be detected."""
        from src.gui.setup.setup_wizard_view import SetupWizardView

        output = self._make_output([
            ("MySQL267", "Running", "MySQL 26.7"),
        ])
        mock_run.return_value = MagicMock(returncode=0, stdout=output, stderr="")

        result = SetupWizardView._find_mysql_service()
        assert result == "MySQL267"

    @patch("subprocess.run")
    def test_detects_mysql80_running(self, mock_run):
        """MySQL80 should still be detected (backward compat)."""
        from src.gui.setup.setup_wizard_view import SetupWizardView

        output = self._make_output([
            ("MySQL80", "Running", "MySQL 8.0"),
        ])
        mock_run.return_value = MagicMock(returncode=0, stdout=output, stderr="")

        result = SetupWizardView._find_mysql_service()
        assert result == "MySQL80"

    @patch("subprocess.run")
    def test_detects_mariadb_running(self, mock_run):
        """MariaDB service should be detected."""
        from src.gui.setup.setup_wizard_view import SetupWizardView

        output = self._make_output([
            ("MariaDB", "Running", "MariaDB Server"),
        ])
        mock_run.return_value = MagicMock(returncode=0, stdout=output, stderr="")

        result = SetupWizardView._find_mysql_service()
        assert result == "MariaDB"

    @patch("subprocess.run")
    def test_skips_stopped_service(self, mock_run):
        """A stopped MySQL267 should NOT be returned by _find_mysql_service."""
        from src.gui.setup.setup_wizard_view import SetupWizardView

        output = self._make_output([
            ("MySQL267", "Stopped", "MySQL 26.7"),
        ])
        mock_run.return_value = MagicMock(returncode=0, stdout=output, stderr="")

        result = SetupWizardView._find_mysql_service()
        assert result is None

    @patch("subprocess.run")
    def test_returns_first_running_when_multiple(self, mock_run):
        """When multiple MySQL services exist, returns the first running one."""
        from src.gui.setup.setup_wizard_view import SetupWizardView

        output = self._make_output([
            ("MySQL80", "Stopped", "MySQL 8.0"),
            ("MySQL267", "Running", "MySQL 26.7"),
        ])
        mock_run.return_value = MagicMock(returncode=0, stdout=output, stderr="")

        result = SetupWizardView._find_mysql_service()
        assert result == "MySQL267"

    @patch("subprocess.run")
    def test_no_mysql_services(self, mock_run):
        """When no MySQL services exist, returns None."""
        from src.gui.setup.setup_wizard_view import SetupWizardView

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = SetupWizardView._find_mysql_service()
        assert result is None

    @patch("subprocess.run")
    def test_powershell_not_available(self, mock_run):
        """Gracefully handles PowerShell not being installed."""
        from src.gui.setup.setup_wizard_view import SetupWizardView

        mock_run.side_effect = FileNotFoundError("powershell not found")

        result = SetupWizardView._find_mysql_service()
        assert result is None

    @patch("subprocess.run")
    def test_powershell_timeout(self, mock_run):
        """Gracefully handles PowerShell timeout."""
        from src.gui.setup.setup_wizard_view import SetupWizardView

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="powershell", timeout=15)

        result = SetupWizardView._find_mysql_service()
        assert result is None


class TestFindMysqlServiceStopped:
    """Tests for SetupWizardView._find_mysql_service_stopped (static method)."""

    POWERSHELL_CMD = [
        "powershell", "-NoProfile", "-Command",
        "Get-Service | Where-Object { $_.Name -match '^(MySQL|MariaDB)' }"
        " | Select-Object Name, Status | Format-List",
    ]

    def _make_output(self, services: list[tuple[str, str]]) -> str:
        """Build Format-List output from (Name, Status) tuples."""
        blocks = []
        for name, status in services:
            blocks.append(f"Name           : {name}")
            blocks.append(f"Status         : {status}")
        return "\n".join(blocks)

    @patch("subprocess.run")
    def test_finds_stopped_mysql267(self, mock_run):
        """Should find a stopped MySQL267 service."""
        from src.gui.setup.setup_wizard_view import SetupWizardView

        output = self._make_output([
            ("MySQL267", "Stopped"),
        ])
        mock_run.return_value = MagicMock(returncode=0, stdout=output, stderr="")

        result = SetupWizardView._find_mysql_service_stopped()
        assert result == "MySQL267"

    @patch("subprocess.run")
    def test_ignores_running_service(self, mock_run):
        """Should return None when service is running (not stopped)."""
        from src.gui.setup.setup_wizard_view import SetupWizardView

        output = self._make_output([
            ("MySQL267", "Running"),
        ])
        mock_run.return_value = MagicMock(returncode=0, stdout=output, stderr="")

        result = SetupWizardView._find_mysql_service_stopped()
        assert result is None

    @patch("subprocess.run")
    def test_no_services(self, mock_run):
        """Should return None when no MySQL services exist."""
        from src.gui.setup.setup_wizard_view import SetupWizardView

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = SetupWizardView._find_mysql_service_stopped()
        assert result is None
