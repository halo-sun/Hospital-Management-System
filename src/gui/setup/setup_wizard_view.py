"""Database setup wizard — one-time configuration for new installations.

Handles the entire "first run on a fresh machine" flow:
  1. Detects MySQL server state (not installed / stopped / unreachable / OK)
  2. Prompts for MySQL admin/root credentials (used transiently)
  3. Creates hospital_db database and hms_app least-privilege user
  4. Runs schema creation via init_db.py
  5. Writes the .env file with hms_app credentials

This view is self-contained: it does NOT depend on the database
connection pool — it creates its own transient connections using
the admin credentials provided by the user.
"""
from __future__ import annotations

import logging
import os
import platform
import subprocess
import sys
from typing import Any, Callable, Optional

import tkinter as tk
from tkinter import ttk, messagebox

logger = logging.getLogger(__name__)

# ── Colour palette (matches Theme flatly) ──────────────────────────
_PRIMARY = "#1B2A4A"
_ACCENT = "#2563EB"
_SUCCESS = "#059669"
_SUCCESS_LIGHT = "#D1FAE5"
_WARNING = "#D97706"
_WARNING_LIGHT = "#FEF3C7"
_DANGER = "#DC2626"
_DANGER_LIGHT = "#FEE2E2"
_BG = "#F0F4F8"
_SURFACE = "#FFFFFF"
_TEXT = "#0F172A"
_MUTED = "#64748B"
_BORDER = "#CBD5E1"
_BTN_EXIT = "#E2E8F0"
_BTN_EXIT_FG = "#334155"


class SetupWizardView(tk.Frame):
    """Multi-step database setup wizard.

    Args:
        parent: Parent tkinter widget.
        on_complete: Callback invoked with ``True`` on success or
            ``False`` if the user cancelled.
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_complete: Optional[Callable[[bool], None]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, bg=_BG, **kwargs)
        self._on_complete = on_complete or (lambda _: None)
        self._admin_user = "root"
        self._admin_pass = ""
        self._hms_password = ""

        # ── Header ──────────────────────────────────────────────
        header = tk.Frame(self, bg=_PRIMARY, height=80)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header, text="🔧  Database Setup Wizard",
            bg=_PRIMARY, fg="white",
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left", padx=20, pady=20)
        tk.Label(
            header, text="Step 1 of 3",
            bg=_PRIMARY, fg="#94A3B8",
            font=("Segoe UI", 10),
        ).pack(side="right", padx=20, pady=20)

        # ── Content area ────────────────────────────────────────
        self._content = tk.Frame(self, bg=_BG)
        self._content.pack(fill="both", expand=True, padx=24, pady=16)

        # ── Status bar ──────────────────────────────────────────
        self._status_frame = tk.Frame(self, bg=_PRIMARY, height=36)
        self._status_frame.pack(fill="x", side="bottom")
        self._status_frame.pack_propagate(False)
        self._status_label = tk.Label(
            self._status_frame, text="Ready",
            bg=_PRIMARY, fg="#CBD5E1",
            font=("Segoe UI", 9), anchor="w",
        )
        self._status_label.pack(side="left", padx=12)

        # Start the wizard
        self._step_detect()

    # ── Status helpers ────────────────────────────────────────────

    def _set_status(self, text: str) -> None:
        self._status_label.configure(text=text)
        self.update_idletasks()

    def _clear_content(self) -> None:
        for w in self._content.winfo_children():
            w.destroy()

    # ── MySQL service discovery (version-agnostic) ─────────────────

    @staticmethod
    def _find_mysql_service() -> Optional[str]:
        """Find any running MySQL/MariaDB Windows service.

        Returns the service display-name if a running MySQL service
        is found, or ``None`` if none is detected.  This is
        version-agnostic: MySQL's installer names its service after
        the version (e.g. MySQL80, MySQL91, MySQL267), so we
        enumerate services and match by prefix instead of hard-coding
        a single name.
        """
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-Service | Where-Object { $_.Name -match '^(MySQL|MariaDB)' }"
                 " | Select-Object Name, Status, DisplayName | Format-List"],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode != 0:
                logger.debug("Get-Service failed: %s", result.stderr.strip())
                return None

            current_name: Optional[str] = None
            current_status: Optional[str] = None
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith("Name"):
                    current_name = line.split(":", 1)[1].strip()
                elif line.startswith("Status"):
                    current_status = line.split(":", 1)[1].strip()
                elif line.startswith("DisplayName"):
                    # End of one service block — check if it was running
                    if current_status and "Running" in current_status:
                        logger.info(
                            "Found running MySQL service: %s (%s)",
                            current_name, line.split(":", 1)[1].strip(),
                        )
                        return current_name
                    # Reset for next block
                    current_name = None
                    current_status = None

            # Handle edge case where last block didn't have DisplayName
            if current_name and current_status and "Running" in current_status:
                logger.info("Found running MySQL service: %s", current_name)
                return current_name

            # No running service found — report any stopped ones
            result2 = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-Service | Where-Object { $_.Name -match '^(MySQL|MariaDB)' }"
                 " | Select-Object Name, Status | Format-Table -AutoSize"],
                capture_output=True, text=True, timeout=15,
            )
            if result2.stdout.strip():
                logger.info(
                    "MySQL services found but none running:\n%s",
                    result2.stdout.strip(),
                )
            return None
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            logger.debug("_find_mysql_service failed: %s", exc)
            return None

    @staticmethod
    def _find_mysql_service_stopped() -> Optional[str]:
        """Find a stopped MySQL/MariaDB Windows service.

        Returns the service name if a stopped MySQL service exists,
        or ``None``.  Used to offer to start the service.
        """
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-Service | Where-Object { $_.Name -match '^(MySQL|MariaDB)' }"
                 " | Select-Object Name, Status | Format-List"],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode != 0:
                return None

            current_name: Optional[str] = None
            current_status: Optional[str] = None
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith("Name"):
                    current_name = line.split(":", 1)[1].strip()
                elif line.startswith("Status"):
                    current_status = line.split(":", 1)[1].strip()
                    if current_name and current_status and "Stopped" in current_status:
                        return current_name
                    current_name = None
                    current_status = None
            return None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

    # ── Step 1: Detect MySQL ──────────────────────────────────────

    def _step_detect(self) -> None:
        self._clear_content()
        self._set_status("Checking MySQL server...")

        card = self._make_card()
        tk.Label(
            card, text="Checking MySQL Server",
            bg=_SURFACE, fg=_TEXT,
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w")
        tk.Label(
            card, text="Verifying MySQL is installed and reachable...",
            bg=_SURFACE, fg=_MUTED, font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(4, 12))

        spinner = tk.Label(
            card, text="⏳", bg=_SURFACE, font=("Segoe UI", 24),
        )
        spinner.pack(pady=8)

        # Run detection in a short delay so the UI paints first
        self.after(200, lambda: self._run_detection(card, spinner))

    def _run_detection(self, card: tk.Frame, spinner: tk.Label) -> None:
        """Probe MySQL and determine its state."""
        state = self._detect_mysql_state()

        spinner.destroy()

        if state == "ok":
            self._set_status("MySQL is reachable ✓")
            self._step_credentials()
            return

        self._clear_content()
        card = self._make_card()

        if state == "not_installed":
            self._render_not_installed(card)
        elif state == "stopped":
            self._render_stopped(card)
        elif state == "wrong_credentials":
            self._render_wrong_credentials(card)
        else:  # unreachable
            self._render_unreachable(card)

    def _detect_mysql_state(self) -> str:
        """Return one of: 'ok', 'not_installed', 'stopped', 'wrong_credentials', 'unreachable'."""
        import mysql.connector
        from mysql.connector import Error

        # First check if mysql binary / service exists
        if platform.system() == "Windows":
            # Version-agnostic: enumerate services matching MySQL* or MariaDB*
            svc_name = self._find_mysql_service()
            if svc_name is None:
                # No running service — check for a stopped one
                stopped = self._find_mysql_service_stopped()
                if stopped:
                    logger.info("MySQL service found but stopped: %s", stopped)
                    return "stopped"
                logger.info("No MySQL/MariaDB service detected on Windows")
                return "not_installed"
            logger.info("MySQL service detected: %s (running)", svc_name)
        else:
            # Linux: check systemctl or service
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", "mysql"],
                    capture_output=True, text=True, timeout=10,
                )
                if result.stdout.strip() != "active":
                    # Try mariadb
                    result2 = subprocess.run(
                        ["systemctl", "is-active", "mariadb"],
                        capture_output=True, text=True, timeout=10,
                    )
                    if result2.stdout.strip() != "active":
                        return "stopped"
            except (FileNotFoundError, subprocess.TimeoutExpired):
                try:
                    result = subprocess.run(
                        ["service", "mysql", "status"],
                        capture_output=True, text=True, timeout=10,
                    )
                    if result.returncode != 0:
                        return "stopped"
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    pass

        # Try connecting with credentials from env (or empty on first run)
        user = os.getenv("DB_USER", "root")
        password = os.getenv("DB_PASSWORD", "")
        logger.info(
            "Attempting MySQL connection as %s (password %s)",
            user, "set" if password else "empty",
        )
        try:
            conn = mysql.connector.connect(
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", "3306")),
                user=user,
                password=password,
                connection_timeout=5,
            )
            conn.close()
            return "ok"
        except Error as e:
            logger.info("MySQL connection failed: errno=%s msg=%s", e.errno, e.msg)
            if e.errno == 1045:  # Access denied
                return "wrong_credentials"
            return "unreachable"

    # ── Render: MySQL not installed ────────────────────────────────

    def _render_not_installed(self, card: tk.Frame) -> None:
        self._set_status("MySQL not detected")
        tk.Label(
            card, text="MySQL Is Not Installed",
            bg=_SURFACE, fg=_DANGER,
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w")
        tk.Label(
            card, text=(
                "MySQL 8.0 or later is required but does not appear to\n"
                "be installed on this system."
            ),
            bg=_SURFACE, fg=_TEXT, font=("Segoe UI", 10),
            justify="left", wraplength=500,
        ).pack(anchor="w", pady=(8, 12))

        info_frame = tk.Frame(card, bg=_WARNING_LIGHT, padx=12, pady=10)
        info_frame.pack(fill="x", pady=(0, 12))
        tk.Label(
            info_frame, text="📌  Next steps:",
            bg=_WARNING_LIGHT, fg=_TEXT,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")
        tk.Label(
            info_frame, text=(
                "1. Download MySQL 8.0 Community Server\n"
                "   from https://dev.mysql.com/downloads/mysql/\n"
                "2. Run the installer and choose \"Developer Default\"\n"
                "3. Remember the root password you set\n"
                "4. Return here and click \"Detect Again\""
            ),
            bg=_WARNING_LIGHT, fg=_TEXT,
            font=("Segoe UI", 9), justify="left",
        ).pack(anchor="w", pady=(4, 0))

        btn_frame = tk.Frame(card, bg=_SURFACE)
        btn_frame.pack(fill="x", pady=(8, 0))
        tk.Button(
            btn_frame, text="Open MySQL Download Page",
            bg=_ACCENT, fg="white", font=("Segoe UI", 10, "bold"),
            activebackground="#1D4ED8", activeforeground="white",
            relief="flat", padx=14, pady=6, cursor="hand2",
            command=self._open_mysql_download,
        ).pack(side="left")
        tk.Button(
            btn_frame, text="Detect Again",
            bg="#E2E8F0", fg=_TEXT, font=("Segoe UI", 10),
            activebackground=_BORDER, activeforeground=_TEXT,
            relief="flat", padx=14, pady=6, cursor="hand2",
            command=self._step_detect,
        ).pack(side="left", padx=(8, 0))
        self._add_exit_button(btn_frame)

    def _open_mysql_download(self) -> None:
        import webbrowser
        webbrowser.open("https://dev.mysql.com/downloads/mysql/")

    # ── Render: MySQL service stopped ──────────────────────────────

    def _render_stopped(self, card: tk.Frame) -> None:
        self._set_status("MySQL service is stopped")
        tk.Label(
            card, text="MySQL Service Is Stopped",
            bg=_SURFACE, fg=_WARNING,
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w")
        tk.Label(
            card, text=(
                "MySQL is installed but the service is not running.\n"
                "Click \"Start MySQL\" to start it automatically."
            ),
            bg=_SURFACE, fg=_TEXT, font=("Segoe UI", 10),
            justify="left", wraplength=500,
        ).pack(anchor="w", pady=(8, 12))

        btn_frame = tk.Frame(card, bg=_SURFACE)
        btn_frame.pack(fill="x", pady=(8, 0))

        self._start_result_label = tk.Label(
            card, text="", bg=_SURFACE, font=("Segoe UI", 9),
            fg=_SUCCESS, anchor="w",
        )
        self._start_result_label.pack(anchor="w", pady=(4, 0))

        tk.Button(
            btn_frame, text="Start MySQL",
            bg=_SUCCESS, fg="white", font=("Segoe UI", 10, "bold"),
            activebackground="#047857", activeforeground="white",
            relief="flat", padx=14, pady=6, cursor="hand2",
            command=self._try_start_mysql,
        ).pack(side="left")
        tk.Button(
            btn_frame, text="Detect Again",
            bg="#E2E8F0", fg=_TEXT, font=("Segoe UI", 10),
            activebackground=_BORDER, activeforeground=_TEXT,
            relief="flat", padx=14, pady=6, cursor="hand2",
            command=self._step_detect,
        ).pack(side="left", padx=(8, 0))
        self._add_exit_button(btn_frame)

    def _try_start_mysql(self) -> None:
        self._start_result_label.configure(text="Starting MySQL service...", fg=_MUTED)
        self.update_idletasks()

        try:
            if platform.system() == "Windows":
                # Discover the actual MySQL service name (version-agnostic)
                svc = self._find_mysql_service_stopped()
                if svc:
                    result = subprocess.run(
                        ["powershell", "-NoProfile", "-Command",
                         f"Start-Service -Name '{svc}'"],
                        capture_output=True, text=True, timeout=30,
                    )
                    if result.returncode == 0:
                        self._start_result_label.configure(text="\u2713 MySQL service started.", fg=_SUCCESS)
                        self.after(1000, self._step_detect)
                        return
                    logger.warning("Start-Service failed for %s: %s", svc, result.stderr.strip())

                # Fallback: try well-known names via net start
                for fallback in ("MySQL80", "MySQL", "mysql"):
                    result = subprocess.run(
                        ["net", "start", fallback],
                        capture_output=True, text=True, timeout=30,
                    )
                    if result.returncode == 0:
                        self._start_result_label.configure(text="\u2713 MySQL service started.", fg=_SUCCESS)
                        self.after(1000, self._step_detect)
                        return
            else:
                result = subprocess.run(
                    ["sudo", "service", "mysql", "start"],
                    capture_output=True, text=True, timeout=30,
                )
                if result.returncode == 0:
                    self._start_result_label.configure(text="\u2713 MySQL service started.", fg=_SUCCESS)
                    self.after(1000, self._step_detect)
                    return

            self._start_result_label.configure(
                text="\u2717 Could not start MySQL. You may need to start it manually.",
                fg=_DANGER,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            self._start_result_label.configure(
                text=f"\u2717 Error: {e}. You may need to start MySQL manually.",
                fg=_DANGER,
            )

    # ── Render: Wrong credentials ──────────────────────────────────

    def _render_wrong_credentials(self, card: tk.Frame) -> None:
        self._set_status("MySQL access denied")
        tk.Label(
            card, text="MySQL Access Denied",
            bg=_SURFACE, fg=_DANGER,
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w")
        tk.Label(
            card, text=(
                "MySQL is running but the current credentials in .env\n"
                "are incorrect. Please enter your MySQL admin credentials\n"
                "below to proceed with setup."
            ),
            bg=_SURFACE, fg=_TEXT, font=("Segoe UI", 10),
            justify="left", wraplength=500,
        ).pack(anchor="w", pady=(8, 12))
        self._render_credential_form(card)

    # ── Render: Unreachable ────────────────────────────────────────

    def _render_unreachable(self, card: tk.Frame) -> None:
        self._set_status("MySQL unreachable")
        tk.Label(
            card, text="Cannot Reach MySQL Server",
            bg=_SURFACE, fg=_DANGER,
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w")
        tk.Label(
            card, text=(
                "MySQL appears to be installed and running, but the\n"
                "application cannot connect to it. This may be a network,\n"
                "port, or authentication issue."
            ),
            bg=_SURFACE, fg=_TEXT, font=("Segoe UI", 10),
            justify="left", wraplength=500,
        ).pack(anchor="w", pady=(8, 12))
        self._render_credential_form(card)

    # ── Shared credential form ─────────────────────────────────────

    def _render_credential_form(self, card: tk.Frame) -> None:
        tk.Label(
            card, text="MySQL Admin Credentials (transient — not saved permanently):",
            bg=_SURFACE, fg=_TEXT, font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        tk.Label(
            card, text="Username:", bg=_SURFACE, fg=_TEXT,
            font=("Segoe UI", 10), anchor="w",
        ).pack(fill="x")
        self._admin_user_var = tk.StringVar(value="root")
        ttk.Entry(
            card, textvariable=self._admin_user_var,
            font=("Segoe UI", 10), width=36,
        ).pack(fill="x", pady=(2, 8), ipady=4)

        tk.Label(
            card, text="Password:", bg=_SURFACE, fg=_TEXT,
            font=("Segoe UI", 10), anchor="w",
        ).pack(fill="x")
        self._admin_pass_var = tk.StringVar()
        ttk.Entry(
            card, textvariable=self._admin_pass_var,
            font=("Segoe UI", 10), width=36, show="*",
        ).pack(fill="x", pady=(2, 8), ipady=4)

        self._cred_error = tk.Label(
            card, text="", bg=_SURFACE, fg=_DANGER,
            font=("Segoe UI", 9), anchor="w", wraplength=460,
        )
        self._cred_error.pack(anchor="w", pady=(0, 8))

        btn_frame = tk.Frame(card, bg=_SURFACE)
        btn_frame.pack(fill="x")
        tk.Button(
            btn_frame, text="Test & Continue",
            bg=_ACCENT, fg="white", font=("Segoe UI", 10, "bold"),
            activebackground="#1D4ED8", activeforeground="white",
            relief="flat", padx=14, pady=6, cursor="hand2",
            command=self._on_credential_submit,
        ).pack(side="left")
        tk.Button(
            btn_frame, text="Detect Again",
            bg="#E2E8F0", fg=_TEXT, font=("Segoe UI", 10),
            activebackground=_BORDER, activeforeground=_TEXT,
            relief="flat", padx=14, pady=6, cursor="hand2",
            command=self._step_detect,
        ).pack(side="left", padx=(8, 0))
        self._add_exit_button(btn_frame)

    def _on_credential_submit(self) -> None:
        user = self._admin_user_var.get().strip()
        pw = self._admin_pass_var.get()

        if not user:
            self._cred_error.configure(text="Username is required.")
            return

        self._cred_error.configure(text="Testing connection...", fg=_MUTED)
        self.update_idletasks()

        logger.info(
            "Credential test: user=%s, host=%s, port=%s",
            user,
            os.getenv("DB_HOST", "localhost"),
            os.getenv("DB_PORT", "3306"),
        )

        import mysql.connector
        from mysql.connector import Error

        try:
            conn = mysql.connector.connect(
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", "3306")),
                user=user,
                password=pw,
                connection_timeout=10,
            )
            conn.close()
            logger.info("Credential test succeeded for user=%s", user)
            self._admin_user = user
            self._admin_pass = pw
            self._cred_error.configure(text="")
            self._step_create_database()
        except Error as e:
            msg = str(e)
            if e.errno == 1045:
                msg = "Access denied — please check your username and password."
            self._cred_error.configure(text=f"✗ {msg}", fg=_DANGER)

    # ── Step 2: Create database + hms_app user ────────────────────

    def _step_create_database(self) -> None:
        self._clear_content()
        self._set_status("Creating database and user...")

        card = self._make_card()
        tk.Label(
            card, text="Setting Up Database",
            bg=_SURFACE, fg=_TEXT,
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w")
        tk.Label(
            card, text="Creating hospital_db database and hms_app user...",
            bg=_SURFACE, fg=_MUTED, font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(4, 12))

        self._progress_text = tk.Label(
            card, text="", bg=_SURFACE, fg=_TEXT,
            font=("Segoe UI", 9), anchor="w", justify="left",
        )
        self._progress_text.pack(anchor="w", fill="x")

        self.after(200, self._run_database_setup)

    def _run_database_setup(self) -> None:
        """Create the database, hms_app user, and generate password."""
        import mysql.connector
        from mysql.connector import Error
        import secrets
        import string

        def _log(msg: str) -> None:
            self._progress_text.configure(text=msg)
            self.update_idletasks()
            logger.info("Setup: %s", msg)

        try:
            _log("Connecting to MySQL as admin...")
            conn = mysql.connector.connect(
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", "3306")),
                user=self._admin_user,
                password=self._admin_pass,
                connection_timeout=10,
            )
            cursor = conn.cursor()

            # 1. Create database
            _log("Creating hospital_db database...")
            cursor.execute(
                "CREATE DATABASE IF NOT EXISTS `hospital_db` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )

            # 2. Generate hms_app password
            alphabet = string.ascii_letters + string.digits + "!@#$%&*"
            self._hms_password = "".join(
                secrets.choice(alphabet) for _ in range(20)
            )

            # 3. Create hms_app user
            _log("Creating hms_app user...")
            db_name = os.getenv("DB_NAME", "hospital_db")
            cursor.execute(
                "CREATE USER IF NOT EXISTS 'hms_app'@'localhost' "
                "IDENTIFIED BY %s",
                (self._hms_password,),
            )

            # 4. Grant DML permissions
            _log("Granting permissions to hms_app...")
            cursor.execute(
                f"GRANT SELECT, INSERT, UPDATE, DELETE ON `{db_name}`.* "
                "TO 'hms_app'@'localhost'"
            )
            cursor.execute("FLUSH PRIVILEGES")

            conn.commit()
            cursor.close()
            conn.close()

            _log("✓ Database and user created successfully.")
            self.after(500, self._step_initialize_schema)

        except Error as e:
            _log(f"✗ Error: {e}")
            logger.exception("Database setup failed")
            self._show_setup_error(str(e))

    # ── Step 3: Initialize schema ──────────────────────────────────

    def _step_initialize_schema(self) -> None:
        self._clear_content()
        self._set_status("Initializing schema...")

        card = self._make_card()
        tk.Label(
            card, text="Initializing Schema",
            bg=_SURFACE, fg=_TEXT,
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w")
        tk.Label(
            card, text="Creating tables and seeding default data...",
            bg=_SURFACE, fg=_MUTED, font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(4, 12))

        self._progress_text = tk.Label(
            card, text="", bg=_SURFACE, fg=_TEXT,
            font=("Segoe UI", 9), anchor="w", justify="left",
        )
        self._progress_text.pack(anchor="w", fill="x")

        self.after(200, self._run_schema_init)

    def _run_schema_init(self) -> None:
        """Initialize schema using the newly created hms_app user."""
        def _log(msg: str) -> None:
            self._progress_text.configure(text=msg)
            self.update_idletasks()
            logger.info("Setup: %s", msg)

        try:
            _log("Connecting as hms_app...")

            # Temporarily set the env vars so init_db picks them up
            os.environ["DB_USER"] = "hms_app"
            os.environ["DB_PASSWORD"] = self._hms_password

            # Initialize the connection pool with the new credentials
            from src.database.connection import DatabaseConnection
            DatabaseConnection.close_pool()  # clear any old pool
            DatabaseConnection.initialize()

            _log("Running schema initialization...")
            from src.database.init_db import initialize_database
            success = initialize_database()

            if success:
                _log("✓ All tables created and verified.")
                self.after(500, self._step_write_env)
            else:
                _log("✗ Schema initialization returned an error.")
                self._show_setup_error(
                    "Schema initialization failed. Check the log for details."
                )

        except Exception as e:
            _log(f"✗ Error: {e}")
            logger.exception("Schema init failed")
            self._show_setup_error(str(e))

    # ── Step 4: Write .env ─────────────────────────────────────────

    def _step_write_env(self) -> None:
        self._clear_content()
        self._set_status("Writing configuration...")

        card = self._make_card()
        tk.Label(
            card, text="Saving Configuration",
            bg=_SURFACE, fg=_TEXT,
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w")
        tk.Label(
            card, text="Writing .env file with hms_app credentials...",
            bg=_SURFACE, fg=_MUTED, font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(4, 12))

        self._progress_text = tk.Label(
            card, text="", bg=_SURFACE, fg=_TEXT,
            font=("Segoe UI", 9), anchor="w", justify="left",
        )
        self._progress_text.pack(anchor="w", fill="x")

        self.after(200, self._run_write_env)

    def _run_write_env(self) -> None:
        def _log(msg: str) -> None:
            self._progress_text.configure(text=msg)
            self.update_idletasks()
            logger.info("Setup: %s", msg)

        try:
            _log("Writing .env file...")

            # Determine project root (one level up from src/)
            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            env_path = os.path.join(project_root, ".env")

            env_content = (
                f"# Auto-generated by HMS Setup Wizard\n"
                f"# ── Database connection ─────────────────────────────\n"
                f"DB_HOST={os.getenv('DB_HOST', 'localhost')}\n"
                f"DB_PORT={os.getenv('DB_PORT', '3306')}\n"
                f"DB_USER=hms_app\n"
                f"DB_PASSWORD={self._hms_password}\n"
                f"DB_NAME={os.getenv('DB_NAME', 'hospital_db')}\n"
                f"\n"
                f"# ── Application ───────────────────────────────────\n"
                f"# SESSION_TIMEOUT=30\n"
                f"# MAX_LOGIN_ATTEMPTS=5\n"
                f"# LOCKOUT_DURATION_MINUTES=15\n"
            )

            with open(env_path, "w") as f:
                f.write(env_content)

            _log(f"✓ .env written to {env_path}")
            self.after(500, self._step_complete)

        except Exception as e:
            _log(f"✗ Error writing .env: {e}")
            logger.exception("Failed to write .env")
            self._show_setup_error(str(e))

    # ── Step 5: Complete ───────────────────────────────────────────

    def _step_complete(self) -> None:
        self._clear_content()
        self._set_status("Setup complete ✓")

        card = self._make_card()
        tk.Label(
            card, text="✅  Database Setup Complete",
            bg=_SURFACE, fg=_SUCCESS,
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", pady=(8, 12))

        tk.Label(
            card, text=(
                "The database is ready. The application will now\n"
                "continue to the first-run admin account setup screen."
            ),
            bg=_SURFACE, fg=_TEXT, font=("Segoe UI", 10),
            justify="left", wraplength=480,
        ).pack(anchor="w", pady=(0, 12))

        info_frame = tk.Frame(card, bg=_SUCCESS_LIGHT, padx=12, pady=10)
        info_frame.pack(fill="x", pady=(0, 12))
        tk.Label(
            info_frame, text=(
                "📌  The hms_app credentials have been saved to .env.\n"
                "The database has 15 tables created and default data seeded.\n"
                "You can now proceed to create your admin account."
            ),
            bg=_SUCCESS_LIGHT, fg=_TEXT, font=("Segoe UI", 9),
            justify="left", wraplength=460,
        ).pack(anchor="w")

        tk.Button(
            card, text="Continue to Application",
            bg=_ACCENT, fg="white", font=("Segoe UI", 11, "bold"),
            activebackground="#1D4ED8", activeforeground="white",
            relief="flat", padx=20, pady=8, cursor="hand2",
            command=lambda: self._on_complete(True),
        ).pack(anchor="w", pady=(8, 0))

    # ── Helpers ────────────────────────────────────────────────────

    def _make_card(self) -> tk.Frame:
        card = tk.Frame(
            self._content, bg=_SURFACE,
            highlightbackground=_BORDER, highlightthickness=1,
            padx=24, pady=20,
        )
        card.pack(fill="x", pady=(0, 12))
        return card

    def _add_exit_button(self, parent: tk.Frame) -> None:
        tk.Button(
            parent, text="Exit",
            bg=_BTN_EXIT, fg=_BTN_EXIT_FG,
            font=("Segoe UI", 10),
            activebackground=_BORDER, activeforeground=_TEXT,
            relief="flat", padx=14, pady=6, cursor="hand2",
            command=lambda: self._on_complete(False),
        ).pack(side="right")

    def _show_setup_error(self, detail: str) -> None:
        self._clear_content()
        card = self._make_card()
        tk.Label(
            card, text="Setup Failed",
            bg=_SURFACE, fg=_DANGER,
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w")
        tk.Label(
            card, text=(
                "An error occurred during database setup.\n"
                "Check the setup log for full details."
            ),
            bg=_SURFACE, fg=_TEXT, font=("Segoe UI", 10),
            justify="left", wraplength=480,
        ).pack(anchor="w", pady=(4, 8))

        # Show truncated error in a styled box
        err_box = tk.Frame(card, bg=_DANGER_LIGHT, padx=12, pady=8)
        err_box.pack(fill="x", pady=(0, 12))
        tk.Label(
            err_box, text=detail[:300],
            bg=_DANGER_LIGHT, fg=_DANGER,
            font=("Segoe UI", 9), anchor="w", justify="left",
            wraplength=460,
        ).pack(anchor="w")

        btn_frame = tk.Frame(card, bg=_SURFACE)
        btn_frame.pack(fill="x")
        tk.Button(
            btn_frame, text="Retry from Start",
            bg=_ACCENT, fg="white", font=("Segoe UI", 10, "bold"),
            activebackground="#1D4ED8", activeforeground="white",
            relief="flat", padx=14, pady=6, cursor="hand2",
            command=self._step_detect,
        ).pack(side="left")
        self._add_exit_button(btn_frame)
