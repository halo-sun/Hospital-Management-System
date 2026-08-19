"""Admin settings view – theme, hospital holidays, and security info.

Follows the admin layout convention (Header.TFrame heading + ttk
LabelFrame sections, as used by the dashboard and management views).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.gui.theme import Theme
from src.gui.common.base_view import BaseView


class SettingsView(BaseView):
    """Admin settings screen with Appearance / Holidays / Security sections."""

    def __init__(
        self,
        parent: tk.Widget,
        on_get_theme: Callable[[], str],
        on_theme_changed: Callable[[str], None],
        on_load_holidays: Callable[[], List[Dict[str, Any]]],
        on_add_holiday: Callable[[date, str], Tuple[bool, str, Optional[int]]],
        on_remove_holiday: Callable[[int], Tuple[bool, str]],
        on_get_lockout: Callable[[], Dict[str, Any]],
        **kwargs: Any,
    ) -> None:
        """Initialise the settings view.

        Args:
            parent: Parent tkinter widget.
            on_get_theme: Callback returning the current theme name.
            on_theme_changed: Callback invoked with the new theme name
                after it has been applied (persists + refreshes the UI).
            on_load_holidays: Callback returning the holiday list.
            on_add_holiday: Callback(date, description) -> (ok, msg, id).
            on_remove_holiday: Callback(holiday_id) -> (ok, msg).
            on_get_lockout: Callback returning the lockout config dict.
            **kwargs: Extra keyword arguments for BaseView.
        """
        super().__init__(parent, **kwargs)
        self._on_get_theme = on_get_theme
        self._on_theme_changed = on_theme_changed
        self._on_load_holidays = on_load_holidays
        self._on_add_holiday = on_add_holiday
        self._on_remove_holiday = on_remove_holiday
        self._on_get_lockout = on_get_lockout
        self._build_ui()
        self._reload_holidays()

    def _build_ui(self) -> None:
        """Construct the settings layout."""
        # ── Header ─────────────────────────────────────────────
        header = ttk.Frame(self, style="Header.TFrame", padding=16)
        header.pack(fill="x")
        ttk.Label(header, text="Settings", style="Heading.TLabel").pack(side="left")
        ttk.Label(
            header, text="  |  System configuration", style="Subheading.TLabel",
        ).pack(side="left", padx=(8, 0))

        # ── Scrollable content ─────────────────────────────────
        canvas = tk.Canvas(self, bg=Theme.BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self._scroll_frame = ttk.Frame(canvas, style="TFrame")
        self._scroll_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self._scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        content = self._scroll_frame
        content.columnconfigure(0, weight=1)

        # ── Appearance ─────────────────────────────────────────
        appearance = ttk.LabelFrame(content, text="Appearance", padding=16)
        appearance.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))

        theme_row = ttk.Frame(appearance, style="TFrame")
        theme_row.pack(fill="x")

        ttk.Label(theme_row, text="Theme:", font=Theme.FONT_BODY).pack(
            side="left", padx=(0, 8),
        )
        self._theme_var = tk.StringVar(value=self._on_get_theme())
        self._theme_combo = ttk.Combobox(
            theme_row, textvariable=self._theme_var, values=Theme.theme_names(),
            width=16, state="readonly", font=Theme.FONT_BODY,
        )
        self._theme_combo.pack(side="left")
        self._theme_combo.bind("<<ComboboxSelected>>", self._handle_theme_selected)

        ttk.Label(
            appearance,
            text="Switches the entire application's look immediately and "
                 "persists the choice for the next restart.",
            style="Muted.TLabel", wraplength=760,
        ).pack(anchor="w", pady=(8, 0))

        # ── Hospital Holidays ──────────────────────────────────
        holidays = ttk.LabelFrame(content, text="Hospital Holidays", padding=16)
        holidays.grid(row=1, column=0, sticky="ew", padx=16, pady=8)

        ttk.Label(
            holidays,
            text="Holidays block appointment booking – the scheduling engine "
                 "refuses slots on these dates, so patients cannot be booked in.",
            style="Muted.TLabel", wraplength=760,
        ).pack(anchor="w", pady=(0, 8))

        # Holiday list
        list_frame = ttk.Frame(holidays, style="TFrame")
        list_frame.pack(fill="x")

        columns = ("date", "description")
        self._holiday_tree = self.create_treeview(
            list_frame, columns=columns,
            headings=("Date", "Description"),
            enable_context_menu=False,
        )
        self._holiday_tree.column("date", width=140, anchor="center")
        self._holiday_tree.column("description", width=560)

        # Add form (inline)
        add_frame = ttk.Frame(holidays, style="TFrame", padding=(0, 10, 0, 0))
        add_frame.pack(fill="x")

        ttk.Label(add_frame, text="Date (YYYY-MM-DD):", font=Theme.FONT_BODY).pack(
            side="left", padx=(0, 6),
        )
        self._holiday_date_var = tk.StringVar()
        ttk.Entry(
            add_frame, textvariable=self._holiday_date_var, width=14,
            font=Theme.FONT_BODY,
        ).pack(side="left", padx=(0, 12))

        ttk.Label(add_frame, text="Description:", font=Theme.FONT_BODY).pack(
            side="left", padx=(0, 6),
        )
        self._holiday_desc_var = tk.StringVar()
        ttk.Entry(
            add_frame, textvariable=self._holiday_desc_var, width=40,
            font=Theme.FONT_BODY,
        ).pack(side="left", padx=(0, 12))

        tk.Button(
            add_frame, text="+ Add Holiday", bg=Theme.SUCCESS, fg=Theme.WHITE,
            font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=12, pady=4,
            command=self._handle_add_holiday,
        ).pack(side="left")

        # Remove button
        btn_frame = ttk.Frame(holidays, style="TFrame", padding=(0, 10, 0, 0))
        btn_frame.pack(fill="x")
        tk.Button(
            btn_frame, text="Remove Selected", bg=Theme.DANGER, fg=Theme.WHITE,
            font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=12, pady=5,
            command=self._handle_remove_holiday,
        ).pack(side="left")

        # ── Security ───────────────────────────────────────────
        security = ttk.LabelFrame(content, text="Security", padding=16)
        security.grid(row=2, column=0, sticky="ew", padx=16, pady=8)

        lockout = self._on_get_lockout()
        attempts = lockout.get("max_login_attempts", "?")
        window_minutes = lockout.get("lockout_duration_minutes", "?")

        ttk.Label(
            security, text=f"Account lockout threshold: {attempts} failed login attempts",
            font=Theme.FONT_BODY,
        ).pack(anchor="w")
        ttk.Label(
            security, text=f"Account lockout window: {window_minutes} minutes",
            font=Theme.FONT_BODY,
        ).pack(anchor="w", pady=(2, 0))
        ttk.Label(
            security,
            text="Read-only for now – changing these values safely requires "
                 "backend support (out of scope for this phase).",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(8, 0))

    # ── Theme ──────────────────────────────────────────────────

    def _handle_theme_selected(self, event=None) -> None:
        """Apply the selected theme immediately and persist via callback."""
        name = self._theme_var.get()
        if not name:
            return
        try:
            Theme.apply_theme(name)
        except ValueError as e:
            self.show_error("Error", str(e))
            return
        self._on_theme_changed(name)

    # ── Hospital holidays ──────────────────────────────────────

    def _reload_holidays(self) -> None:
        """Refresh the holiday list from the controller."""
        self._holiday_tree.delete(*self._holiday_tree.get_children())
        for holiday in self._on_load_holidays():
            holiday_date = holiday.get("holiday_date", "")
            if hasattr(holiday_date, "strftime"):
                holiday_date = holiday_date.strftime("%Y-%m-%d")
            self._holiday_tree.insert(
                "", "end",
                iid=str(holiday.get("holiday_id", "")),
                values=(holiday_date, holiday.get("description", "")),
            )

    def _handle_add_holiday(self) -> None:
        """Validate and add a holiday, then refresh the list."""
        raw_date = self._holiday_date_var.get().strip()
        try:
            holiday_date = date.fromisoformat(raw_date)
        except ValueError:
            self.show_warning("Warning", "Invalid date. Use YYYY-MM-DD.")
            return

        description = self._holiday_desc_var.get().strip()
        if not description:
            self.show_warning("Warning", "Please enter a description.")
            return

        success, msg, _ = self._on_add_holiday(holiday_date, description)
        if success:
            self._holiday_date_var.set("")
            self._holiday_desc_var.set("")
            self._reload_holidays()
        else:
            self.show_error("Error", msg)

    def _handle_remove_holiday(self) -> None:
        """Remove the selected holiday after a confirmation step."""
        selection = self._holiday_tree.selection()
        if not selection:
            self.show_warning("Warning", "Please select a holiday to remove.")
            return
        holiday_id = int(selection[0])

        confirmed = messagebox.askyesno(
            "Confirm",
            "Remove this holiday?\n\n"
            "Appointment booking will no longer be blocked on this date.",
            parent=self,
        )
        if not confirmed:
            return

        success, msg = self._on_remove_holiday(holiday_id)
        if success:
            self._reload_holidays()
        else:
            self.show_error("Error", msg)
