"""Standalone database setup utility for Hospital Management System.

Run independently to set up the database before the main application:

    python src/setup.py

This can also be packaged as HMS-Setup.exe via PyInstaller for
distribution with the installer.

What it does:
  1. Detects MySQL server state (not installed / stopped / unreachable / OK)
  2. Prompts for MySQL admin/root credentials (transient, not stored permanently)
  3. Creates hospital_db database and hms_app least-privilege user
  4. Runs schema creation via init_db.py
  5. Writes the .env file with hms_app credentials

After this runs successfully, the main application's first-run
admin setup screen takes over for account creation.
"""
from __future__ import annotations

import logging
import os
import sys

# Ensure project root is on the path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config import app_config


def main() -> None:
    """Launch the standalone database setup wizard."""
    # Configure logging to file + console
    log_dir = app_config.LOGS_DIR
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "setup.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger = logging.getLogger("setup")
    logger.info("HMS Setup Utility started (log: %s)", log_file)

    # Verify tkinter is available
    try:
        import tkinter as tk
    except ImportError:
        logger.error("tkinter is not available. Install python3-tk on Linux.")
        print(
            "Error: tkinter is not available.\n"
            "On Linux, install it with: sudo apt install python3-tk\n"
            "On Windows, reinstall Python with 'tcl/tk and IDLE' checked."
        )
        sys.exit(1)

    from src.gui.setup.setup_wizard_view import SetupWizardView
    from src.gui.theme import Theme

    root = tk.Tk()
    root.title(f"{app_config.name} — Database Setup")
    root.geometry("620x720")
    root.configure(bg=Theme.BG)
    root.resizable(False, False)

    # Try to set the app icon
    icon_path = os.path.join(app_config.ASSETS_DIR, "icon.ico")
    if os.path.exists(icon_path):
        try:
            root.iconbitmap(icon_path)
        except tk.TclError:
            pass

    Theme.apply_theme("flatly")

    def _on_complete(success: bool) -> None:
        if success:
            logger.info("Setup completed successfully.")
            from tkinter import messagebox
            messagebox.showinfo(
                "Setup Complete",
                "Database is ready. You can now launch the main application.",
            )
        else:
            logger.info("Setup was cancelled by the user.")
        root.destroy()

    view = SetupWizardView(root, on_complete=_on_complete)
    view.pack(fill="both", expand=True)

    root.mainloop()


if __name__ == "__main__":
    main()
