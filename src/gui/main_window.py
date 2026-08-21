"""Main application window that hosts all views.

Manages the top bar, sidebar, content area, and status bar.
Provides global keyboard shortcuts and a loading indicator
for navigation.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Optional, Dict, Any, Callable

from src.gui.theme import Theme
from src.gui.common.sidebar import Sidebar
from src.utils.formatters import DISPLAY_DATETIME_FORMAT
from src.config import app_config


class MainWindow:
    """Root application window with status bar and keyboard shortcuts.

    Responsibilities:
    * Top bar (title, user info, logout)
    * Sidebar (role-based navigation)
    * Content area (view swapping)
    * Status bar (user feedback, clock)
    * Global keyboard shortcuts
    """

    def __init__(
        self,
        on_logout: Optional[Callable] = None,
        on_session_expired: Optional[Callable] = None,
    ) -> None:
        """Initialise the main window.

        Args:
            on_logout: Optional callback invoked when the user logs out.
            on_session_expired: Optional callback invoked on the clock
                ticker; should return True (and handle logout) when the
                inactivity session timeout has elapsed.
        """
        self._on_logout = on_logout
        self._on_session_expired = on_session_expired
        self._root = tk.Tk()
        self._root.title(f"{app_config.name} v{app_config.version}")
        self._root.geometry(f"{app_config.window_width}x{app_config.window_height}")
        self._root.minsize(app_config.min_window_width, app_config.min_window_height)
        self._root.configure(bg=Theme.BG)

        # Make content area expand on window resize
        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(1, weight=1)

        Theme.configure_ttk()

        # ── Top bar ───────────────────────────────────────────
        self._build_top_bar()

        # ── Body (sidebar + content) ──────────────────────────
        self._body = tk.Frame(self._root, bg=Theme.BG)
        self._body.grid(row=1, column=0, sticky="nsew")
        self._body.columnconfigure(1, weight=1)
        self._body.rowconfigure(0, weight=1)

        self._sidebar = Sidebar(self._body, on_navigate=self._on_navigate)
        self._sidebar.grid(row=0, column=0, sticky="ns")

        self._content_frame = tk.Frame(self._body, bg=Theme.BG)
        self._content_frame.grid(row=0, column=1, sticky="nsew")
        self._content_frame.columnconfigure(0, weight=1)
        self._content_frame.rowconfigure(0, weight=1)

        # ── Status bar ────────────────────────────────────────
        self._build_status_bar()

        self._current_view: Optional[tk.Frame] = None
        self._nav_handlers: Dict[str, Callable] = {}
        self._current_key: Optional[str] = None

        # ── Global keyboard shortcuts ─────────────────────────
        self._bind_shortcuts()

    # ── Top bar ──────────────────────────────────────────────

    def _build_top_bar(self) -> None:
        """Construct the top bar with title, user info, and logout."""
        self._top_bar = tk.Frame(self._root, bg=Theme.SURFACE, height=Theme.TOPBAR_HEIGHT)
        self._top_bar.grid(row=0, column=0, sticky="ew")
        self._top_bar.pack_propagate(False)
        # Shadow effect at bottom of top bar
        tk.Frame(self._top_bar, bg=Theme.BORDER, height=1).pack(side="bottom", fill="x")

        tk.Label(
            self._top_bar, text="🏥 Hospital Management System",
            bg=Theme.SURFACE, fg=Theme.HEADING, font=Theme.FONT_HEADING,
        ).pack(side="left", padx=16)

        self._user_info_frame = tk.Frame(self._top_bar, bg=Theme.SURFACE)
        self._user_info_frame.pack(side="right", padx=16)

        self._user_label = tk.Label(
            self._user_info_frame, text="", bg=Theme.SURFACE,
            fg=Theme.SURFACE_TEXT, font=Theme.FONT_SMALL,
        )
        self._user_label.pack(side="left", padx=(0, 12))

        self._logout_btn = tk.Button(
            self._user_info_frame, text="Logout", bg=Theme.DANGER, fg=Theme.WHITE,
            font=Theme.FONT_SMALL, activebackground=Theme.DANGER_HOVER,
            activeforeground=Theme.WHITE, cursor="hand2", bd=0,
            padx=12, pady=4, command=self._handle_logout,
        )
        self._logout_btn.pack(side="left")

    # ── Status bar ───────────────────────────────────────────

    def _build_status_bar(self) -> None:
        """Construct the bottom status bar with message area and clock."""
        self._status_bar = tk.Frame(self._root, bg=Theme.PRIMARY, height=28)
        self._status_bar.grid(row=2, column=0, sticky="ew")
        self._status_bar.pack_propagate(False)

        self._status_message = tk.Label(
            self._status_bar, text="Ready", bg=Theme.PRIMARY,
            fg=Theme.LIGHT_TEXT, font=Theme.FONT_SMALL, anchor="w",
        )
        self._status_message.pack(side="left", padx=12)

        self._status_clock = tk.Label(
            self._status_bar, text="", bg=Theme.PRIMARY,
            fg=Theme.LIGHT_TEXT, font=Theme.FONT_SMALL, anchor="e",
        )
        self._status_clock.pack(side="right", padx=12)

        self._update_clock()

    def _update_clock(self) -> None:
        """Update the status bar clock every 30 seconds.

        Also enforces the inactivity session timeout on the same
        ticker: if the session has expired the callback performs the
        logout flow (which destroys this window), so the clock is not
        rescheduled.
        """
        now = datetime.now().strftime(DISPLAY_DATETIME_FORMAT)
        self._status_clock.configure(text=now)
        if self._on_session_expired and self._on_session_expired():
            return
        self._root.after(30000, self._update_clock)

    def set_status(self, message: str) -> None:
        """Set the status bar message text.

        Args:
            message: Status text.
        """
        self._status_message.configure(text=message)

    def refresh_theme(self) -> None:
        """Rebuild chrome and the current view with the active Theme palette.

        ``Theme.apply_theme`` swaps the palette class attributes and
        re-applies the global ttk styles; tk widgets capture colours at
        build time, so the top bar, status bar, sidebar buttons, and the
        current content view are rebuilt here to reflect the new theme
        immediately.
        """
        Theme.configure_ttk()
        self._top_bar.destroy()
        self._build_top_bar()
        self._status_bar.destroy()
        self._build_status_bar()
        self._sidebar.set_active(self._current_key or "")
        if self._current_key:
            factory = self._nav_handlers.get(self._current_key)
            if factory:
                view = factory(self._content_frame)
                self.show_content(view)

    # ── Global keyboard shortcuts ───────────────────────────

    def _bind_shortcuts(self) -> None:
        """Bind global keyboard shortcuts."""
        # Navigation shortcuts
        self._root.bind("<Control-d>", lambda e: self.navigate_to("dashboard"))
        self._root.bind("<Control-p>", lambda e: self.navigate_to("register_patient"))
        self._root.bind("<Control-a>", lambda e: self.navigate_to("analytics"))
        self._root.bind("<Control-r>", lambda e: self.navigate_to("reports"))

        # Refresh
        self._root.bind("<F5>", lambda e: self._refresh_current_view())

        # Logout
        self._root.bind(
            "<Control-q>", lambda e: self._handle_logout(),
        )
        self._root.bind("<Control-l>", lambda e: self._handle_logout())

        # Escape — show dashboard
        self._root.bind("<Escape>", lambda e: self.navigate_to(self._current_key or "dashboard"))

        # Help
        self._root.bind("<F1>", lambda e: self._show_shortcuts_help())

    def _show_shortcuts_help(self) -> None:
        """Show a keyboard shortcuts reference dialog."""
        shortcuts = [
            ("F5", "Refresh current view"),
            ("Ctrl+D", "Dashboard"),
            ("Ctrl+R", "Reports"),
            ("Ctrl+A", "Analytics"),
            ("Ctrl+L / Ctrl+Q", "Logout"),
            ("Escape", "Return to current view"),
            ("F1", "This help"),
        ]
        text = "\n".join(f"{k:20s} {d}" for k, d in shortcuts)
        messagebox.showinfo("Keyboard Shortcuts", text, parent=self._root)

    def _refresh_current_view(self) -> None:
        """Re-navigate to the current view (F5 refresh)."""
        if self._current_key:
            self._on_navigate(self._current_key, force=True)

    # ── Public API ──────────────────────────────────────────

    def set_user(self, user: Dict[str, Any]) -> None:
        """Update the top bar with the logged-in user's info.

        Args:
            user: User dictionary with 'full_name' and 'role_name'.
        """
        name = user.get("full_name") or user.get("username", "")
        role = user.get("role_name", "")
        self._user_label.configure(text=f"{name}  ({role})")
        self.set_status(f"Logged in as {name} ({role})")

    def set_sidebar_items(self, items) -> None:
        """Populate the sidebar navigation.

        Args:
            items: List of (key, label) tuples.
        """
        self._sidebar.set_items(items)

    def register_view(self, key: str, factory: Callable) -> None:
        """Register a view factory for a navigation key.

        Args:
            key: Navigation key.
            factory: Callable that returns a tk.Frame when called with parent.
        """
        self._nav_handlers[key] = factory

    def navigate_to(self, key: str, force: bool = False) -> None:
        """Programmatically navigate to a view.

        Args:
            key: Navigation key.
            force: If True, re-create the view even if it's already
                   the current view (useful for refresh).
        """
        self._on_navigate(key, force=force)

    def show_content(self, view: tk.Frame) -> None:
        """Display a frame in the content area.

        Args:
            view: The frame to display.
        """
        if self._current_view:
            self._current_view.destroy()
        self._current_view = view
        self._current_view.pack(fill="both", expand=True, padx=0, pady=0)

    def get_current_content(self) -> Optional[tk.Frame]:
        """Return the currently displayed content frame (if any).

        Returns:
            The current view frame or None.
        """
        return self._current_view

    def get_content_parent(self) -> tk.Frame:
        """Return the content frame that should serve as parent for new views.

        Returns:
            The content area frame.
        """
        return self._content_frame

    def get_root(self) -> tk.Tk:
        """Return the underlying tkinter root window.

        Returns:
            The root Tk instance.
        """
        return self._root

    def run(self) -> None:
        """Start the tkinter main loop."""
        self._root.mainloop()

    def close(self) -> None:
        """Close the main window."""
        self._root.quit()
        self._root.destroy()

    # ── Visual refresh confirmation ─────────────────────────

    def _flash_content(self) -> None:
        """Briefly flash the content area to confirm a refresh."""
        if self._current_view is None:
            return
        try:
            self._current_view.configure(bg=Theme.ACCENT_LIGHT)
            self._root.after(
                150,
                lambda: self._current_view.configure(bg=Theme.BG)
                if self._current_view is not None else None,
            )
        except tk.TclError:
            pass  # view may have been destroyed

    # ── Internal ────────────────────────────────────────────

    def _on_navigate(self, key: str, force: bool = False) -> None:
        """Handle sidebar navigation.

        Args:
            key: The navigation key clicked.
            force: If True, re-create the view even when it matches
                   the current view (used by refresh button / F5).
        """
        if key == self._current_key and not force:
            return

        factory = self._nav_handlers.get(key)
        if not factory:
            return

        self._sidebar.set_active(key)
        self._current_key = key
        self.set_status(f"Navigating to {key.replace('_', ' ').title()}...")

        view = factory(self._content_frame)
        self.show_content(view)
        self.set_status(f"View: {key.replace('_', ' ').title()}")
        # Flash the content area to confirm the refresh visually
        if force:
            self._flash_content()

    def _handle_logout(self) -> None:
        """Prompt the user and log out."""
        if messagebox.askyesno("Logout", "Are you sure you want to log out?", parent=self._root):
            if self._current_view:
                self._current_view.destroy()
                self._current_view = None
            self._current_key = None
            self.set_status("Logged out")
            if self._on_logout:
                self._on_logout()
