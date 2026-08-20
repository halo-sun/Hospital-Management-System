"""Login screen GUI with refined hospital-themed design."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable, Dict, Any
from src.config.settings import AppConfig
from src.gui.theme import Theme
from src.gui.common.base_view import BaseView, create_button


class LoginView(BaseView):
    """Login screen with username/password fields, Remember Me, and keyboard navigation."""

    def __init__(
        self,
        parent: tk.Widget,
        on_login: Callable,
        saved_username: str = "",
        **kwargs: Any,
    ) -> None:
        """Initialise the login view.

        Args:
            parent: Parent tkinter widget.
            on_login: Callback invoked with (username, password, remember_me).
            saved_username: Pre-fill the username field (from Remember Me).
            **kwargs: Extra keyword arguments for BaseView.
        """
        super().__init__(parent, **kwargs)
        self._on_login = on_login
        self._saved_username = saved_username
        self._show_password = False
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the login form layout."""
        self.configure(style="TFrame")

        # ── Background with decorative gradient effect ─────────
        # Use a darker top band simulating a header
        header_bg = tk.Frame(self, bg=Theme.PRIMARY, height=180)
        header_bg.pack(fill="x", side="top")
        header_bg.pack_propagate(False)

        tk.Label(
            header_bg, text="🏥", bg=Theme.PRIMARY, fg=Theme.WHITE,
            font=("Segoe UI", 48),
        ).pack(pady=(20, 0))
        tk.Label(
            header_bg, text="Hospital Management System",
            bg=Theme.PRIMARY, fg=Theme.WHITE, font=Theme.FONT_TITLE,
        ).pack(pady=(4, 0))

        # ── Center card ────────────────────────────────────────
        center = tk.Frame(self, bg=Theme.BG)
        center.pack(fill="both", expand=True)

        # Card
        card = tk.Frame(
            center, bg=Theme.SURFACE, padx=40, pady=32,
            highlightbackground=Theme.BORDER, highlightthickness=1,
        )
        card.place(relx=0.5, rely=0.45, anchor="center")

        # Card title
        tk.Label(
            card, text="Sign In", bg=Theme.SURFACE, fg=Theme.HEADING,
            font=Theme.FONT_HEADING,
        ).pack(anchor="w", pady=(0, 4))
        tk.Label(
            card, text="Enter your credentials to continue",
            bg=Theme.SURFACE, fg=Theme.SURFACE_MUTED, font=Theme.FONT_SMALL,
        ).pack(anchor="w", pady=(0, 24))

        # ── Username ───────────────────────────────────────────
        tk.Label(
            card, text="Username", bg=Theme.SURFACE, fg=Theme.SURFACE_TEXT,
            font=Theme.FONT_BODY, anchor="w",
        ).pack(fill="x")
        self._username_var = tk.StringVar()
        self._username_entry = ttk.Entry(
            card, textvariable=self._username_var,
            font=Theme.FONT_BODY, width=32,
        )
        self._username_entry.pack(fill="x", pady=(4, 16), ipady=6)
        self._username_entry.focus_set()

        # ── Password ───────────────────────────────────────────
        tk.Label(
            card, text="Password", bg=Theme.SURFACE, fg=Theme.SURFACE_TEXT,
            font=Theme.FONT_BODY, anchor="w",
        ).pack(fill="x")

        pw_frame = tk.Frame(card, bg=Theme.SURFACE)
        pw_frame.pack(fill="x", pady=(4, 8))

        self._password_var = tk.StringVar()
        self._password_entry = ttk.Entry(
            pw_frame, textvariable=self._password_var,
            font=Theme.FONT_BODY, show="*", width=30,
        )
        self._password_entry.pack(side="left", fill="x", expand=True, ipady=6)
        self._password_entry.bind("<Return>", lambda e: self._handle_login())

        # Password visibility toggle
        self._eye_btn = tk.Button(
            pw_frame, text="👁", bg=Theme.SURFACE, fg=Theme.SURFACE_MUTED,
            font=Theme.FONT_SMALL, bd=0, cursor="hand2",
            activebackground=Theme.LIGHT, activeforeground=Theme.SURFACE_TEXT,
            command=self._toggle_password,
        )
        self._eye_btn.pack(side="left", padx=(4, 0))

        # ── Remember Me ────────────────────────────────────────
        self._remember_var = tk.BooleanVar(value=bool(self._saved_username))
        remember_cb = tk.Checkbutton(
            card, text="Remember Me", variable=self._remember_var,
            bg=Theme.SURFACE, fg=Theme.SURFACE_TEXT, font=Theme.FONT_SMALL,
            activebackground=Theme.SURFACE, activeforeground=Theme.SURFACE_TEXT,
            cursor="hand2", selectcolor=Theme.SURFACE,
        )
        remember_cb.pack(anchor="w", pady=(0, 8))

        # ── Error label ────────────────────────────────────────
        self._error_var = tk.StringVar()
        self._error_label = tk.Label(
            card, textvariable=self._error_var, bg=Theme.SURFACE,
            fg=Theme.DANGER, font=Theme.FONT_SMALL, anchor="w", wraplength=320,
        )
        self._error_label.pack(fill="x", pady=(0, 8))

        # ── Login button ───────────────────────────────────────
        self._login_btn = tk.Button(
            card, text="Sign In", bg=Theme.ACCENT, fg=Theme.WHITE,
            font=Theme.FONT_BUTTON_BOLD, activebackground=Theme.ACCENT_HOVER,
            activeforeground=Theme.WHITE, cursor="hand2", bd=0,
            padx=20, pady=10, command=self._handle_login,
        )
        self._login_btn.pack(fill="x", ipady=4)

        # ── Version ────────────────────────────────────────────
        tk.Label(
            card, text=f"v{AppConfig.VERSION}  |  Secure Login",
            bg=Theme.SURFACE, fg=Theme.SURFACE_MUTED, font=Theme.FONT_SMALL,
        ).pack(pady=(16, 0))

        # Pre-fill username if saved
        if self._saved_username:
            self._username_var.set(self._saved_username)
            self._password_entry.focus_set()

    # ── Actions ──────────────────────────────────────────────

    def _toggle_password(self) -> None:
        """Toggle password visibility."""
        self._show_password = not self._show_password
        self._password_entry.configure(
            show="" if self._show_password else "*",
        )
        self._eye_btn.configure(
            text="👁" if not self._show_password else "👁‍🗨",
        )

    def _handle_login(self) -> None:
        """Validate inputs and invoke the login callback."""
        username = self._username_var.get().strip()
        password = self._password_var.get()

        if not username:
            self._show_error("Username is required.")
            self._username_entry.focus_set()
            return
        if not password:
            self._show_error("Password is required.")
            self._password_entry.focus_set()
            return

        self._error_var.set("")
        self._login_btn.configure(state="disabled", text="Signing in...")
        self._remember_var.set(self._remember_var.get())
        self.update_idletasks()
        self._on_login(username, password, self._remember_var.get())

    def _show_error(self, message: str) -> None:
        """Display an error message.

        Args:
            message: The error text.
        """
        self._error_var.set(message)

    def show_error_message(self, message: str) -> None:
        """Public method to show an error from outside the class.

        Re-enables the login button so the user can try again.

        Args:
            message: The error text to display.
        """
        self._show_error(message)
        self._login_btn.configure(state="normal", text="Sign In")

    def clear_fields(self) -> None:
        """Clear username and password fields."""
        self._username_var.set("")
        self._password_var.set("")
        self._error_var.set("")
        self._login_btn.configure(state="normal", text="Sign In")
