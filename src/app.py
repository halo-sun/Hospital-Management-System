"""Main application entry point for the Hospital Management System.

Wires together controllers, views, and the tkinter main window.
Role-specific view registration has been extracted into factory
classes under ``src.factories``.
"""
from __future__ import annotations

import logging
import sys
from typing import Optional, Dict, Any

import tkinter as tk
from tkinter import messagebox

from src.config import app_config, db_config
from src.constants import Role
from src.database.connection import DatabaseConnection
from src.database.init_db import initialize_database

logger = logging.getLogger("app")

# ── Startup dependency check ───────────────────────────────────
# Non-blocking: each critical third-party dependency is probed at
# startup and a clear WARNING is logged if one is missing, so a missing
# package surfaces immediately in the logs instead of hours later when
# the one screen that needs it renders blank (e.g. matplotlib powers
# the analytics charts but is lazily imported).
CRITICAL_DEPENDENCIES = (
    # (import name, what breaks if missing)
    ("matplotlib", "analytics charts will not render"),
    ("numpy", "analytics charts (matplotlib) will not render"),
    ("mysql.connector", "database connectivity is unavailable"),
    ("bcrypt", "password hashing is unavailable"),
    ("reportlab", "PDF exports will not work"),
    ("openpyxl", "Excel exports will not work"),
    ("PIL", "image handling / avatars will not work"),
    ("tkcalendar", "calendar pickers will not work"),
)


def check_critical_dependencies() -> None:
    """Log a WARNING for each missing critical dependency.

    Intentionally non-blocking: the app still starts, but operators see
    exactly which feature will be degraded in the startup log rather
    than discovering it as a blank screen later.
    """
    import importlib
    missing = []
    for module_name, consequence in CRITICAL_DEPENDENCIES:
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append((module_name, consequence))
            logger.warning(
                "Missing dependency '%s' — %s. "
                "Install with: pip install -r requirements.txt",
                module_name, consequence,
            )
    if missing:
        logger.warning(
            "Startup dependency check found %d missing package(s); "
            "affected features are listed above.",
            len(missing),
        )
    else:
        logger.debug("Startup dependency check passed — all critical packages present")

from src.controllers.auth_controller import AuthController
from src.controllers.setup_controller import SetupController
from src.controllers.patient_controller import PatientController
from src.controllers.doctor_controller import DoctorController
from src.controllers.staff_controller import StaffController
from src.controllers.appointment_controller import AppointmentController
from src.controllers.report_controller import ReportController
from src.controllers.clinical_controller import ClinicalController

from src.gui.theme import Theme
from src.gui.main_window import MainWindow
from src.gui.auth.login_view import LoginView
from src.gui.auth.first_run_setup_view import FirstRunSetupView

from src.factories.admin_factory import AdminViewFactory
from src.factories.doctor_factory import DoctorViewFactory
from src.factories.receptionist_factory import ReceptionistViewFactory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


class Application:
    """Top-level application orchestrator.

    Responsibilities are limited to:
    * Database initialisation
    * Login / logout lifecycle
    * Delegating role-specific setup to factories

    View factories own the per-role navigation and widget registration.
    """

    def __init__(self) -> None:
        """Initialise controllers and internal state."""
        self._setup_ctrl = SetupController()
        self._auth_ctrl = AuthController()
        self._patient_ctrl = PatientController(auth_ctrl=self._auth_ctrl)
        self._doctor_ctrl = DoctorController(auth_ctrl=self._auth_ctrl)
        self._staff_ctrl = StaffController(auth_ctrl=self._auth_ctrl)
        self._appt_ctrl = AppointmentController(auth_ctrl=self._auth_ctrl)
        self._report_ctrl = ReportController(auth_ctrl=self._auth_ctrl)
        self._clinical_ctrl = ClinicalController(auth_ctrl=self._auth_ctrl)

        self._main_window: Optional[MainWindow] = None
        self._login_view: Optional[LoginView] = None
        self._setup_view: Optional[FirstRunSetupView] = None
        self._root: Optional[tk.Tk] = None

    # ── Lifecycle ──────────────────────────────────────────────

    def run(self) -> None:
        """Start the application.

        After checking critical dependencies and initialising the
        database the startup screen is chosen from the database itself:
        if no admin account exists the first-run setup screen is shown,
        otherwise the normal login screen.  The check runs at every
        launch — the users table is the source of truth, not a marker
        file.
        """
        logger.info("Starting Hospital Management System...")
        check_critical_dependencies()
        self._init_database()
        if self._setup_ctrl.has_admin():
            self._show_login()
        else:
            logger.info("No admin account found — showing first-run setup.")
            self._show_first_run_setup()

    def _get_persisted_theme(self) -> str:
        """Return the admin-chosen theme name for this launch.

        Reads the persisted theme from ``app_settings``; falls back to
        the default theme when the setting is missing or the table is
        unavailable.  The palette is applied once the Tk root exists
        (``ttk.Style()`` requires a root).

        Returns:
            A valid theme name (e.g. 'flatly' or 'darkly').
        """
        try:
            from src.services.settings_service import SettingsService
            theme_name = SettingsService().get_theme()
            if theme_name in Theme.THEMES:
                return theme_name
        except Exception:
            logger.exception("Failed to read persisted theme")
        return "flatly"

    # ── Database ───────────────────────────────────────────────

    def _init_database(self, max_retries: int = 3) -> None:
        """Initialise the database schema and seed data.

        Attempts a pre-flight connection test before the real
        initialisation.  On failure a dialog offers **Retry** (up to
        *max_retries* times) or **Run Database Setup** which launches
        the standalone setup wizard and returns here on success.

        Args:
            max_retries: How many times the user may click Retry
                before the option is exhausted.
        """
        for attempt in range(1, max_retries + 1):
            if not DatabaseConnection.test_connection():
                logger.warning(
                    "Pre-flight DB check failed (attempt %d/%d)",
                    attempt, max_retries,
                )
                action = self._show_db_error_dialog(
                    attempt=attempt,
                    max_retries=max_retries,
                )
                if action == "retry":
                    DatabaseConnection.close_pool()
                    continue
                elif action == "setup":
                    self._launch_setup_wizard()
                    DatabaseConnection.close_pool()
                    continue
                else:  # cancel / window closed
                    sys.exit(0)
            else:
                # Connection good — proceed with schema init
                break
        else:
            # Exhausted retries without a successful connection
            logger.error("DB pre-flight failed after %d attempts", max_retries)
            sys.exit(1)

        try:
            DatabaseConnection.initialize()
            initialize_database()
            logger.info("Database ready.")
        except Exception as e:
            # Log the full detail server-side; only a generic message is
            # shown to the user so connection details never leak to the GUI.
            logger.exception("Database initialisation failed")
            messagebox.showerror(
                "Database Error",
                "Failed to initialise the database schema.\n\n"
                "Full details have been written to the setup log.\n"
                "Please check the log and try again.",
            )
            sys.exit(1)

    def _show_db_error_dialog(
        self, attempt: int, max_retries: int,
    ) -> str:
        """Show a database connection error dialog with Retry / Setup / Cancel.

        Returns:
            ``"retry"``, ``"setup"``, or ``"cancel"``.
        """
        root = tk.Tk()
        root.withdraw()
        root.title("Database Connection")
        root.geometry("460x260")
        root.configure(bg="#F0F4F8")
        root.resizable(False, False)

        remaining = max_retries - attempt
        frame = tk.Frame(root, bg="#F0F4F8", padx=24, pady=20)
        frame.pack(fill="both", expand=True)

        # Icon + title
        tk.Label(
            frame, text="⚠️", font=("Segoe UI", 32),
            bg="#F0F4F8", fg="#D97706",
        ).pack(anchor="w")
        tk.Label(
            frame, text="Cannot connect to MySQL",
            font=("Segoe UI", 13, "bold"),
            bg="#F0F4F8", fg="#0F172A", anchor="w",
        ).pack(fill="x", pady=(4, 8))
        tk.Label(
            frame, text=(
                f"The application could not reach the MySQL server at\n"
                f"{db_config.host}:{db_config.port}.\n\n"
                f"Please ensure MySQL is installed and running, then\n"
                f"check the connection settings in your .env file."
            ),
            font=("Segoe UI", 10), bg="#F0F4F8", fg="#334155",
            anchor="w", justify="left", wraplength=400,
        ).pack(fill="x", pady=(0, 12))

        result = {"action": "cancel"}

        btn_frame = tk.Frame(frame, bg="#F0F4F8")
        btn_frame.pack(fill="x")

        def _on_retry():
            result["action"] = "retry"
            root.destroy()

        def _on_setup():
            result["action"] = "setup"
            root.destroy()

        def _on_cancel():
            result["action"] = "cancel"
            root.destroy()

        if remaining > 0:
            tk.Button(
                btn_frame, text=f"Retry ({remaining} left)",
                font=("Segoe UI", 10, "bold"), bg="#2563EB", fg="white",
                activebackground="#1D4ED8", activeforeground="white",
                relief="flat", padx=16, pady=6, cursor="hand2",
                command=_on_retry,
            ).pack(side="left")

        tk.Button(
            btn_frame, text="Run Database Setup",
            font=("Segoe UI", 10), bg="#059669", fg="white",
            activebackground="#047857", activeforeground="white",
            relief="flat", padx=16, pady=6, cursor="hand2",
            command=_on_setup,
        ).pack(side="left", padx=(8, 0))

        tk.Button(
            btn_frame, text="Exit",
            font=("Segoe UI", 10), bg="#E2E8F0", fg="#334155",
            activebackground="#CBD5E1", activeforeground="#0F172A",
            relief="flat", padx=16, pady=6, cursor="hand2",
            command=_on_cancel,
        ).pack(side="right")

        root.mainloop()
        return result["action"]

    def _launch_setup_wizard(self) -> None:
        """Launch the standalone database setup wizard.

        Creates a temporary Tk root, shows the setup wizard, and
        waits for it to complete before returning to the main app.
        """
        try:
            from src.gui.setup.setup_wizard_view import SetupWizardView
        except ImportError:
            logger.exception("Setup wizard module not found")
            messagebox.showerror(
                "Setup Unavailable",
                "The database setup wizard could not be loaded.\n"
                "Please run the setup utility manually:",
            )
            return

        wizard_root = tk.Tk()
        wizard_root.title(f"{app_config.name} — Database Setup")
        wizard_root.geometry("620x720")
        wizard_root.configure(bg="#F0F4F8")
        wizard_root.resizable(False, False)

        def _on_wizard_complete(success: bool) -> None:
            wizard_root.destroy()
            if success:
                messagebox.showinfo(
                    "Setup Complete",
                    "Database is ready. The application will now continue.",
                )

        view = SetupWizardView(wizard_root, on_complete=_on_wizard_complete)
        view.pack(fill="both", expand=True)
        wizard_root.mainloop()

    # ── First-run setup ────────────────────────────────────────

    def _show_first_run_setup(self) -> None:
        """Display the first-run administrator setup screen.

        This is the only screen reachable when no admin account
        exists — there is no skip option.
        """
        self._root = tk.Tk()
        self._root.title(f"{app_config.name} - Initial Setup")
        self._root.geometry("500x660")
        self._root.configure(bg=Theme.BG)
        Theme.apply_theme(self._get_persisted_theme())

        self._setup_view = FirstRunSetupView(
            self._root,
            on_submit=self._handle_setup_submit,
        )
        self._setup_view.pack(fill="both", expand=True)
        self._root.mainloop()

    def _handle_setup_submit(
        self, username: str, password: str, confirm_password: str,
    ) -> None:
        """Process the first-run setup form.

        Validation is enforced server-side by the controller, which
        returns per-field errors for inline display.  On success the
        setup window is closed and the user is redirected to the
        login screen with a confirmation.

        Args:
            username: The desired admin username.
            password: The desired password.
            confirm_password: Password confirmation.
        """
        if self._setup_view:
            self._setup_view.set_submitting(True)

        success, message, field_errors = self._setup_ctrl.create_admin(
            username, password, confirm_password,
        )

        if not success:
            if self._setup_view:
                self._setup_view.set_submitting(False)
                self._setup_view.show_field_errors(field_errors)
                if message and not field_errors:
                    self._setup_view.show_error_message(message)
            return

        self._setup_view.destroy()
        self._root.destroy()

        messagebox.showinfo(
            "Setup Complete",
            "Admin account created — please log in.",
        )
        self._show_login()

    # ── Login / Logout / Remember Me ──────────────────────────

    def _show_login(self) -> None:
        """Display the login screen.

        If no valid Remember-Me token exists the user is prompted
        for credentials.  If a token exists the session is restored
        automatically, skipping the login screen entirely.
        """
        # Attempt automatic session restore from Remember-Me token
        restored_user = self._auth_ctrl.restore_session()
        if restored_user:
            self._show_main_window(restored_user)
            return

        saved_username = ""
        # We could attempt a partial restore here in the future

        self._root = tk.Tk()
        self._root.title(f"{app_config.name} - Login")
        self._root.geometry("500x500")
        self._root.configure(bg=Theme.BG)
        Theme.apply_theme(self._get_persisted_theme())

        self._login_view = LoginView(
            self._root,
            on_login=self._handle_login,
            saved_username=saved_username,
        )
        self._login_view.pack(fill="both", expand=True)
        self._root.mainloop()

    def _handle_login(
        self, username: str, password: str, remember_me: bool = False,
    ) -> None:
        """Process a login attempt with optional Remember-Me.

        Args:
            username: The entered username.
            password: The entered password.
            remember_me: Whether to persist a session token.
        """
        try:
            success, message, user = self._auth_ctrl.login(
                username, password, remember_me=remember_me,
            )
        except Exception as e:
            # Catch structured exceptions for better UX
            self._login_view.show_error_message(str(e))
            return

        if not success:
            self._login_view.show_error_message(message)
            return

        self._login_view.destroy()
        self._root.destroy()

        self._show_main_window(user)

    def _handle_logout(self) -> None:
        """Log out the user and return to the login screen."""
        self._auth_ctrl.logout()
        if self._main_window:
            self._main_window.close()
            self._main_window = None
        self._show_login()

    def _handle_session_expired(self) -> bool:
        """Force a logout when the inactivity session timeout elapses.

        Called by ``MainWindow``'s clock ticker.  Returns True (and
        performs the logout flow) if the session has expired.

        Returns:
            True if the session expired and logout was triggered.
        """
        if not self._auth_ctrl.is_session_expired():
            return False
        logger.info("Session expired due to inactivity — forcing logout.")
        messagebox.showwarning(
            "Session Expired",
            "Your session has expired due to inactivity. Please log in again.",
        )
        self._handle_logout()
        return True

    # ── Role-based main window ─────────────────────────────────

    def _show_main_window(self, user: Dict[str, Any]) -> None:
        """Launch the main window after successful login.

        Delegates side-bar and view registration to the appropriate
        factory for the user's role.

        Args:
            user: The authenticated user dictionary.
        """
        role = user.get("role_name", "")

        self._main_window = MainWindow(
            on_logout=self._handle_logout,
            on_session_expired=self._handle_session_expired,
        )
        self._main_window.set_user(user)

        if role == Role.ADMIN:
            factory = AdminViewFactory(
                self._main_window,
                self._auth_ctrl,
                self._doctor_ctrl,
                self._staff_ctrl,
                self._appt_ctrl,
                self._report_ctrl,
            )
            factory.setup()
        elif role == Role.DOCTOR:
            factory = DoctorViewFactory(
                self._main_window,
                self._auth_ctrl,
                self._doctor_ctrl,
                self._patient_ctrl,
                self._appt_ctrl,
                self._clinical_ctrl,
            )
            factory.setup(user)
        elif role == Role.RECEPTIONIST:
            factory = ReceptionistViewFactory(
                self._main_window,
                self._auth_ctrl,
                self._patient_ctrl,
                self._doctor_ctrl,
                self._appt_ctrl,
                self._report_ctrl,
            )
            factory.setup(user)

        self._main_window.run()


def main() -> None:
    """Application entry point."""
    app_config.ensure_directories()
    app = Application()
    app.run()


if __name__ == "__main__":
    main()
