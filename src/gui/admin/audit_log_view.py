"""Admin audit log viewer – read-only table of user activity.

Audit logs are immutable.  This view deliberately exposes **no**
create/edit/delete actions and no action column: it only lists and
filters entries (date range + action type).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from datetime import date, timedelta
from typing import Any, Callable, Dict, List, Optional

from src.gui.theme import Theme
from src.gui.common.base_view import BaseView
from src.constants import AuditAction
from src.utils.formatters import format_date, parse_date_for_input, DISPLAY_DATE_FORMAT, DISPLAY_DATETIME_FORMAT

ALL_ACTIONS = "All Actions"

# Curated from the real AuditAction strings the model uses, so every
# dropdown option matches actual audit entries.
ACTION_FILTER_OPTIONS = [
    ALL_ACTIONS,
    AuditAction.LOGIN,
    AuditAction.LOGIN_FAILED,
    AuditAction.LOGOUT,
    AuditAction.CREATE,
    AuditAction.UPDATE,
    AuditAction.DELETE,
    AuditAction.PATIENT_REGISTER,
    AuditAction.PATIENT_UPDATE,
    AuditAction.DOCTOR_CREATE,
    AuditAction.DOCTOR_UPDATE,
    AuditAction.APPOINTMENT_BOOK,
    AuditAction.APPOINTMENT_CANCEL,
    AuditAction.APPOINTMENT_RESCHEDULE,
    AuditAction.PRESCRIPTION_CREATE,
    AuditAction.REPORT_UPLOAD,
    AuditAction.PASSWORD_RESET,
]


class AuditLogView(BaseView):
    """Read-only audit log table with date-range and action filters."""

    def __init__(
        self,
        parent: tk.Widget,
        on_load_data: Callable[[date, date, Optional[str]], List[Dict[str, Any]]],
        **kwargs: Any,
    ) -> None:
        """Initialise the audit log view.

        Args:
            parent: Parent tkinter widget.
            on_load_data: Callback(start_date, end_date, action) returning
                matching audit rows.  ``action`` is None for "All Actions".
            **kwargs: Extra keyword arguments for BaseView.
        """
        super().__init__(parent, **kwargs)
        self._on_load_data = on_load_data
        self._end_date = date.today()
        self._start_date = self._end_date - timedelta(days=7)
        self._build_ui()
        self._load_data()

    def _build_ui(self) -> None:
        """Construct the header, filter bar, and read-only table."""
        # ── Header ─────────────────────────────────────────────
        header = ttk.Frame(self, style="Header.TFrame", padding=16)
        header.pack(fill="x")
        ttk.Label(header, text="Audit Logs", style="Heading.TLabel").pack(side="left")
        ttk.Label(
            header, text="  |  Read-only activity trail", style="Subheading.TLabel",
        ).pack(side="left", padx=(8, 0))

        # ── Filter bar ─────────────────────────────────────────
        filter_frame = ttk.Frame(self, style="TFrame", padding=(16, 8))
        filter_frame.pack(fill="x")

        ttk.Label(filter_frame, text="From:", font=Theme.FONT_BODY).pack(side="left", padx=(0, 4))
        self._start_var = tk.StringVar(value=format_date(self._start_date))
        ttk.Entry(
            filter_frame, textvariable=self._start_var, width=12, font=Theme.FONT_BODY,
        ).pack(side="left", padx=(0, 12))

        ttk.Label(filter_frame, text="To:", font=Theme.FONT_BODY).pack(side="left", padx=(0, 4))
        self._end_var = tk.StringVar(value=format_date(self._end_date))
        ttk.Entry(
            filter_frame, textvariable=self._end_var, width=12, font=Theme.FONT_BODY,
        ).pack(side="left", padx=(0, 12))

        ttk.Label(filter_frame, text="Action:", font=Theme.FONT_BODY).pack(side="left", padx=(0, 4))
        self._action_var = tk.StringVar(value=ALL_ACTIONS)
        ttk.Combobox(
            filter_frame, textvariable=self._action_var, values=ACTION_FILTER_OPTIONS,
            width=22, state="readonly", font=Theme.FONT_BODY,
        ).pack(side="left", padx=(0, 12))

        # Quick date ranges
        for label, days_back in [("Last 7 Days", 7), ("Last 30 Days", 30), ("Last 90 Days", 90)]:
            tk.Button(
                filter_frame, text=label, bg=Theme.LIGHT, fg=Theme.DARK_TEXT,
                font=Theme.FONT_SMALL, cursor="hand2", bd=0, padx=8, pady=2,
                command=lambda d=days_back: self._set_date_range(d),
            ).pack(side="left", padx=(0, 6))

        tk.Button(
            filter_frame, text="Refresh", bg=Theme.ACCENT, fg=Theme.WHITE,
            font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=12, pady=3,
            command=self._load_data,
        ).pack(side="left", padx=(12, 0))

        # ── Table (read-only – no action column) ───────────────
        table_frame = ttk.Frame(self, style="TFrame", padding=16)
        table_frame.pack(fill="both", expand=True)

        columns = ("timestamp", "user", "action", "entity", "details")
        self._tree = self.create_treeview(
            table_frame, columns=columns,
            headings=("Timestamp", "User", "Action", "Entity", "Details"),
            enable_context_menu=False,
        )
        self._tree.column("timestamp", width=150)
        self._tree.column("user", width=140)
        self._tree.column("action", width=170)
        self._tree.column("entity", width=130)
        self._tree.column("details", width=420)

        # Empty-state label (shown in place of the table when no rows match)
        self._empty_label = ttk.Label(
            table_frame, text="No matching audit entries",
            style="Muted.TLabel", anchor="center", font=Theme.FONT_SUBHEADING,
        )

    # ── Filtering ──────────────────────────────────────────────

    def _set_date_range(self, days_back: int) -> None:
        """Set a quick date range and reload.

        Args:
            days_back: Number of days to go back from today.
        """
        self._end_date = date.today()
        self._start_date = self._end_date - timedelta(days=days_back)
        self._start_var.set(format_date(self._start_date))
        self._end_var.set(format_date(self._end_date))
        self._load_data()

    def _load_data(self) -> None:
        """Parse the filters, fetch rows, and refresh the table."""
        start = parse_date_for_input(self._start_var.get().strip())
        end = parse_date_for_input(self._end_var.get().strip())
        if start is None or end is None:
            self.show_warning("Warning", f"Invalid date format. Use {DISPLAY_DATE_FORMAT}.")
            return

        if start > end:
            self.show_warning("Warning", "Start date must be before end date.")
            return

        action = self._action_var.get()
        if action == ALL_ACTIONS:
            action = None

        rows = self._on_load_data(start, end, action)
        self.populate(rows)

    # ── Table population ───────────────────────────────────────

    def populate(self, rows: List[Dict[str, Any]]) -> None:
        """Fill the tree with audit rows or show the empty state.

        Args:
            rows: List of audit record dicts.
        """
        self._tree.delete(*self._tree.get_children())

        if not rows:
            self._tree.grid_remove()
            self._empty_label.grid(row=0, column=0, columnspan=2, sticky="nsew")
            return

        self._empty_label.grid_remove()
        self._tree.grid()

        for row in rows:
            self._tree.insert("", "end", values=(
                self._format_timestamp(row.get("timestamp")),
                row.get("username", ""),
                row.get("action", ""),
                row.get("target_entity", ""),
                self._format_details(row),
            ))

    # ── Display helpers ────────────────────────────────────────

    @staticmethod
    def _format_timestamp(value: Any) -> str:
        """Render a timestamp as ``DD-MM-YYYY HH:MM:SS``.

        Args:
            value: A datetime/date, or a pre-formatted string.

        Returns:
            The formatted timestamp string.
        """
        from datetime import datetime as _dt
        if hasattr(value, "strftime"):
            return value.strftime("%d-%m-%Y %H:%M:%S")
        # Try to parse a string timestamp
        if isinstance(value, str) and value:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M:%S"):
                try:
                    return _dt.strptime(value, fmt).strftime("%d-%m-%Y %H:%M:%S")
                except ValueError:
                    continue
        return str(value)

    @staticmethod
    def _format_details(row: Dict[str, Any]) -> str:
        """Build a human-readable Details cell from the audit fields.

        Prefers the changed/created values, then the previous values,
        then falls back to the target entity and ID.

        Args:
            row: An audit record dict.

        Returns:
            A short summary string.
        """
        new_vals = row.get("new_values") or {}
        old_vals = row.get("old_values") or {}
        entity = row.get("target_entity", "")
        target_id = row.get("target_id", "")

        def _summarize(values: Dict[str, Any]) -> str:
            parts = [f"{k}: {v}" for k, v in list(values.items())[:5]]
            return ", ".join(parts)

        if isinstance(new_vals, dict) and new_vals:
            summary = _summarize(new_vals)
            return summary or f"{entity} #{target_id}"
        if isinstance(old_vals, dict) and old_vals:
            return f"Previous: {_summarize(old_vals)}"
        if target_id:
            return f"{entity} #{target_id}"
        return entity or ""
