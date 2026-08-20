"""First-run setup screen – administrator account creation.

Shown instead of the login screen when no admin account exists yet.
Styled consistently with ``LoginView`` (same header band, centred
card, and theme).  This is the only screen reachable before an admin
exists — there is no skip option.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict

from src.config.settings import AppConfig
from src.gui.theme import Theme
from src.gui.common.base_view import BaseView


class FirstRunSetupView(BaseView):
    """Admin account creation form with per-field inline errors."""

    def __init__(
        self,
        parent: tk.Widget,
        on_submit: Callable[[str, str, str], None],
        **kwargs: Any,
    ) -> None:
        """Initialise the first-run setup view.

        Args:
            parent: Parent tkinter widget.
            on_submit: Callback invoked with (username, password, confirm).
            **kwargs: Extra keyword arguments for BaseView.
        """
        super().__init__(parent, **kwargs)
        self._on_submit = on_submit
        self._show_password = False
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the setup form layout."""
        self.configure(style="TFrame")

        # ── Header band ────────────────────────────────────────
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

        card = tk.Frame(
            center, bg=Theme.SURFACE, padx=40, pady=28,
            highlightbackground=Theme.BORDER, highlightthickness=1,
        )
        card.place(relx=0.5, rely=0.46, anchor="center")

        tk.Label(
            card, text="Initial Setup", bg=Theme.SURFACE, fg=Theme.HEADING,
            font=Theme.FONT_HEADING,
        ).pack(anchor="w", pady=(0, 4))
        tk.Label(
            card, text=(
                "No administrator account found. Create the first\n"
                "admin account to activate the system."
            ),
            bg=Theme.SURFACE, fg=Theme.SURFACE_MUTED, font=Theme.FONT_SMALL,
            justify="left",
        ).pack(anchor="w", pady=(0, 20))

        # ── Admin Username ─────────────────────────────────────
        self._add_field_label(card, "Admin Username")
        self._username_var = tk.StringVar()
        self._username_entry = ttk.Entry(
            card, textvariable=self._username_var,
            font=Theme.FONT_BODY, width=32,
        )
        self._username_entry.pack(fill="x", pady=(4, 0), ipady=6)
        self._username_entry.focus_set()
        self._username_error_var = tk.StringVar()
        self._add_error_label(card, self._username_error_var)

        # ── Password ───────────────────────────────────────────
        self._add_field_label(card, "Password")
        pw_frame = tk.Frame(card, bg=Theme.SURFACE)
        pw_frame.pack(fill="x", pady=(4, 0))

        self._password_var = tk.StringVar()
        self._password_entry = ttk.Entry(
            pw_frame, textvariable=self._password_var,
            font=Theme.FONT_BODY, show="*", width=30,
        )
        self._password_entry.pack(side="left", fill="x", expand=True, ipady=6)

        self._eye_btn = tk.Button(
            pw_frame, text="👁", bg=Theme.SURFACE, fg=Theme.SURFACE_MUTED,
            font=Theme.FONT_SMALL, bd=0, cursor="hand2",
            activebackground=Theme.LIGHT, activeforeground=Theme.SURFACE_TEXT,
            command=self._toggle_password,
        )
        self._eye_btn.pack(side="left", padx=(4, 0))

        self._password_error_var = tk.StringVar()
        self._add_error_label(card, self._password_error_var)

        tk.Label(
            card, text="Minimum 10 characters with uppercase, lowercase, number and symbol.",
            bg=Theme.SURFACE, fg=Theme.SURFACE_MUTED, font=Theme.FONT_SMALL,
            anchor="w", wraplength=320, justify="left",
        ).pack(fill="x", pady=(0, 0))

        # ── Confirm Password ───────────────────────────────────
        self._add_field_label(card, "Confirm Password")
        self._confirm_var = tk.StringVar()
        self._confirm_entry = ttk.Entry(
            card, textvariable=self._confirm_var,
            font=Theme.FONT_BODY, show="*", width=32,
        )
        self._confirm_entry.pack(fill="x", pady=(4, 0), ipady=6)
        self._confirm_entry.bind("<Return>", lambda e: self._handle_submit())
        self._confirm_error_var = tk.StringVar()
        self._add_error_label(card, self._confirm_error_var)

        # ── General error label ────────────────────────────────
        self._general_error_var = tk.StringVar()
        self._add_error_label(card, self._general_error_var)

        # ── Submit button ──────────────────────────────────────
        self._submit_btn = tk.Button(
            card, text="Create Admin Account", bg=Theme.ACCENT, fg=Theme.WHITE,
            font=Theme.FONT_BUTTON_BOLD, activebackground=Theme.ACCENT_HOVER,
            activeforeground=Theme.WHITE, cursor="hand2", bd=0,
            padx=20, pady=10, command=self._handle_submit,
        )
        self._submit_btn.pack(fill="x", ipady=4, pady=(8, 0))

        tk.Label(
            card, text=f"v{AppConfig.VERSION}  |  Secure First-Run Setup",
            bg=Theme.SURFACE, fg=Theme.SURFACE_MUTED, font=Theme.FONT_SMALL,
        ).pack(pady=(12, 0))

    # ── Small helpers ──────────────────────────────────────────

    @staticmethod
    def _add_field_label(parent: tk.Widget, text: str) -> None:
        """Add a muted field label above an entry."""
        tk.Label(
            parent, text=text, bg=Theme.SURFACE, fg=Theme.SURFACE_TEXT,
            font=Theme.FONT_BODY, anchor="w",
        ).pack(fill="x", pady=(12, 0))

    @staticmethod
    def _add_error_label(parent: tk.Widget, var: tk.StringVar) -> None:
        """Add a red inline error label bound to a StringVar."""
        tk.Label(
            parent, textvariable=var, bg=Theme.SURFACE,
            fg=Theme.DANGER, font=Theme.FONT_SMALL, anchor="w",
            wraplength=320, justify="left",
        ).pack(fill="x", pady=(2, 0))

    # ── Actions ────────────────────────────────────────────────

    def _toggle_password(self) -> None:
        """Toggle password visibility."""
        self._show_password = not self._show_password
        self._password_entry.configure(
            show="" if self._show_password else "*",
        )
        self._eye_btn.configure(
            text="👁" if not self._show_password else "👁‍🗨",
        )

    def _handle_submit(self) -> None:
        """Clear previous errors and invoke the submit callback."""
        self.clear_errors()
        self._on_submit(
            self._username_var.get(),
            self._password_var.get(),
            self._confirm_var.get(),
        )

    # ── Public API for the application layer ───────────────────

    def show_field_errors(self, errors: Dict[str, str]) -> None:
        """Display per-field inline validation errors.

        Args:
            errors: Dict mapping field name to error message.
        """
        if "username" in errors:
            self._username_error_var.set(errors["username"])
        if "password" in errors:
            self._password_error_var.set(errors["password"])
        if "confirm" in errors:
            self._confirm_error_var.set(errors["confirm"])

    def show_error_message(self, message: str) -> None:
        """Display a general (non-field) error message.

        Args:
            message: The error text.
        """
        self._general_error_var.set(message)

    def clear_errors(self) -> None:
        """Clear all inline error labels."""
        self._username_error_var.set("")
        self._password_error_var.set("")
        self._confirm_error_var.set("")
        self._general_error_var.set("")

    def set_submitting(self, submitting: bool) -> None:
        """Enable/disable the submit button while processing.

        Args:
            submitting: Whether the form is being submitted.
        """
        self._submit_btn.configure(
            state="disabled" if submitting else "normal",
            text="Creating account..." if submitting else "Create Admin Account",
        )
        self.update_idletasks()
