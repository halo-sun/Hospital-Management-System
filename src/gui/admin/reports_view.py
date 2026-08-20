"""Reports view — tabular report generation with PDF/Excel export.

Provides a selection of report types backed by ``ReportController``,
renders results in a sortable Treeview, and offers PDF / Excel export
via ``export_service``.
"""
from __future__ import annotations

import logging
import os
from datetime import date, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from src.gui.theme import Theme
from src.gui.common.base_view import BaseView

logger = logging.getLogger(__name__)


# Report type definitions: (key, label, needs_date_range)
REPORT_TYPES: List[Tuple[str, str, bool]] = [
    ("daily_appointments", "Daily Appointments", True),
    ("monthly_appointments", "Monthly Appointments", True),
    ("doctor_workload", "Doctor Workload", False),
    ("department_stats", "Department Statistics", False),
    ("patient_demographics", "Patient Demographics", False),
    ("cancellation_rate", "Cancellation Rate", True),
    ("peak_hours", "Peak Hours (by Hour)", False),
]


class ReportsView(BaseView):
    """Dedicated reports view with type selection, data table, and export.

    Provides:
    * Report type dropdown (daily/monthly appointments, doctor workload, …)
    * Date range selector (shown only when the selected report needs one)
    * Quick range buttons (Last 7/30/90 days)
    * Sortable Treeview displaying report results
    * PDF and Excel export buttons
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_generate: Callable[[str, Optional[date], Optional[date]], List[Dict[str, Any]]],
        on_export_pdf: Callable[[str, List[str], List[List[Any]], str, str], Tuple[bool, str]],
        on_export_excel: Callable[[str, List[str], List[List[Any]], str, str], Tuple[bool, str]],
        **kwargs: Any,
    ) -> None:
        """Initialise the reports view.

        Args:
            parent: Parent tkinter widget.
            on_generate: Callback(report_type, start_date, end_date) →
                list of row dicts for the selected report.
            on_export_pdf: Callback(filepath, headers, rows, title,
                report_type) → (success, message).
            on_export_excel: Callback(filepath, headers, rows, title,
                report_type) → (success, message).
        """
        super().__init__(parent, **kwargs)
        self._on_generate = on_generate
        self._on_export_pdf = on_export_pdf
        self._on_export_excel = on_export_excel

        # State
        self._start_date = date.today() - timedelta(days=30)
        self._end_date = date.today()
        self._current_report_type = REPORT_TYPES[0][0]
        self._current_headers: List[str] = []
        self._current_rows: List[List[Any]] = []
        self._current_title = ""

        self._build_ui()

    # ── UI construction ──────────────────────────────────────

    def _build_ui(self) -> None:
        """Construct the reports layout."""
        # Header
        header = ttk.Frame(self, style="Header.TFrame", padding=16)
        header.pack(fill="x")
        ttk.Label(header, text="Reports", style="Heading.TLabel").pack(side="left")
        ttk.Label(
            header, text="  |  Generate and export hospital reports",
            style="Subheading.TLabel",
        ).pack(side="left", padx=(8, 0))

        # ── Controls bar ──────────────────────────────────────
        controls = ttk.Frame(self, style="TFrame", padding=(16, 8))
        controls.pack(fill="x")

        # Report type selector
        ttk.Label(controls, text="Report:", font=Theme.FONT_BODY).pack(
            side="left", padx=(0, 4),
        )
        self._type_var = tk.StringVar(value=REPORT_TYPES[0][1])
        type_combo = ttk.Combobox(
            controls,
            textvariable=self._type_var,
            values=[label for _, label, _ in REPORT_TYPES],
            width=28,
            state="readonly",
            font=Theme.FONT_BODY,
        )
        type_combo.pack(side="left", padx=(0, 16))
        type_combo.bind("<<ComboboxSelected>>", lambda e: self._on_type_change())

        # Date range (conditional — hidden when report doesn't need dates)
        self._date_frame = ttk.Frame(controls, style="TFrame")

        ttk.Label(self._date_frame, text="From:", font=Theme.FONT_BODY).pack(
            side="left", padx=(0, 4),
        )
        self._start_var = tk.StringVar(value=self._start_date.isoformat())
        ttk.Entry(
            self._date_frame, textvariable=self._start_var, width=12,
            font=Theme.FONT_BODY,
        ).pack(side="left", padx=(0, 8))

        ttk.Label(self._date_frame, text="To:", font=Theme.FONT_BODY).pack(
            side="left", padx=(0, 4),
        )
        self._end_var = tk.StringVar(value=self._end_date.isoformat())
        ttk.Entry(
            self._date_frame, textvariable=self._end_var, width=12,
            font=Theme.FONT_BODY,
        ).pack(side="left", padx=(0, 8))

        # Quick range buttons
        for label, days_back in [
            ("7 Days", 7), ("30 Days", 30), ("90 Days", 90),
        ]:
            tk.Button(
                self._date_frame, text=label, bg=Theme.LIGHT,
                fg=Theme.DARK_TEXT, font=Theme.FONT_SMALL, cursor="hand2",
                bd=0, padx=8, pady=2,
                command=lambda d=days_back: self._set_quick_range(d),
            ).pack(side="left", padx=(0, 4))

        self._date_frame.pack(side="left")

        # Generate button
        tk.Button(
            controls, text="Generate Report", bg=Theme.ACCENT,
            fg=Theme.WHITE, font=Theme.FONT_BUTTON_BOLD, cursor="hand2",
            bd=0, padx=14, pady=3, command=self._generate_report,
        ).pack(side="left", padx=(12, 0))

        # ── Export buttons ────────────────────────────────────
        tk.Button(
            controls, text="Export PDF", bg=Theme.DANGER,
            fg=Theme.WHITE, font=Theme.FONT_SMALL_BOLD, cursor="hand2",
            bd=0, padx=10, pady=3, command=self._export_pdf,
        ).pack(side="right", padx=(0, 4))

        tk.Button(
            controls, text="Export Excel", bg=Theme.SUCCESS,
            fg=Theme.WHITE, font=Theme.FONT_SMALL_BOLD, cursor="hand2",
            bd=0, padx=10, pady=3, command=self._export_excel,
        ).pack(side="right", padx=(0, 8))

        # ── Results table ─────────────────────────────────────
        table_frame = ttk.Frame(self, style="TFrame", padding=16)
        table_frame.pack(fill="both", expand=True)

        self._tree = self.create_treeview(
            table_frame,
            columns=(),
            headings=(),
            height=20,
        )

        # Empty state
        self._empty_label = ttk.Label(
            table_frame,
            text="Select a report type and click 'Generate Report'",
            style="Muted.TLabel", anchor="center",
            font=Theme.FONT_SUBHEADING,
        )
        self._empty_label.grid(row=0, column=0, columnspan=2, sticky="nsew")

        # ── Status bar ────────────────────────────────────────
        status_frame = ttk.Frame(self, style="TFrame", padding=(16, 4, 16, 12))
        status_frame.pack(fill="x")
        self._status_label = ttk.Label(
            status_frame, text="", style="Muted.TLabel",
        )
        self._status_label.pack(side="left")

    # ── Helpers ──────────────────────────────────────────────

    def _on_type_change(self) -> None:
        """Handle report type dropdown change — show/hide date range."""
        label = self._type_var.get()
        for key, lbl, needs_date in REPORT_TYPES:
            if lbl == label:
                self._current_report_type = key
                if needs_date:
                    self._date_frame.pack(side="left")
                else:
                    self._date_frame.pack_forget()
                break

    def _set_quick_range(self, days_back: int) -> None:
        """Set a quick date range and update the entry fields.

        Args:
            days_back: Number of days to go back from today.
        """
        self._end_date = date.today()
        self._start_date = self._end_date - timedelta(days=days_back)
        self._start_var.set(self._start_date.isoformat())
        self._end_var.set(self._end_date.isoformat())

    def _parse_dates(self) -> Tuple[Optional[date], Optional[date]]:
        """Parse and validate the date range from the entry fields.

        Returns:
            Tuple of (start_date, end_date), or (None, None) on error.
        """
        report_type = self._current_report_type
        needs_date = any(k == report_type and nd for k, _, nd in REPORT_TYPES)

        if not needs_date:
            return None, None

        try:
            start = date.fromisoformat(self._start_var.get().strip())
            end = date.fromisoformat(self._end_var.get().strip())
        except (ValueError, AttributeError):
            messagebox.showwarning(
                "Warning", "Invalid date format. Use YYYY-MM-DD.", parent=self,
            )
            return None, None

        if start > end:
            messagebox.showwarning(
                "Warning", "Start date must be before end date.", parent=self,
            )
            return None, None

        return start, end

    # ── Report generation ────────────────────────────────────

    def _generate_report(self) -> None:
        """Generate the selected report and display results."""
        start, end = self._parse_dates()
        if start is None and any(
            k == self._current_report_type and nd for k, _, nd in REPORT_TYPES
        ):
            return  # date parse failed

        try:
            rows = self._on_generate(self._current_report_type, start, end)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate report:\n{e}", parent=self)
            logger.exception("Report generation failed")
            return

        self._display_results(rows)

    def _display_results(self, rows: List[Dict[str, Any]]) -> None:
        """Render report data into the treeview.

        Rebuilds the tree columns dynamically based on the data keys,
        then populates the rows.

        Args:
            rows: List of dictionaries from the report generator.
        """
        # Determine headers from data keys
        if not rows:
            headers: List[str] = []
        else:
            headers = list(rows[0].keys())

        # Pretty-print header names
        display_headings = [h.replace("_", " ").title() for h in headers]

        # Rebuild tree with new columns
        self._tree.delete(*self._tree.get_children())
        self._tree["columns"] = headers
        for col in headers:
            self._tree.heading(col, text=col.replace("_", " ").title(), anchor="w")
            self._tree.column(col, anchor="w", minwidth=80, width=140)

        # Sort headers for stable column order
        self._current_headers = display_headings
        self._current_rows = [
            [row.get(h, "") for h in headers] for row in rows
        ]

        # Populate
        for row_data in self._current_rows:
            self._tree.insert("", "end", values=row_data)

        # Toggle empty state
        if rows:
            self._empty_label.grid_remove()
            self._tree.grid()
        else:
            self._tree.grid_remove()
            self._empty_label.grid(row=0, column=0, columnspan=2, sticky="nsew")

        self.apply_default_sort(self._tree)

        # Update status
        report_label = self._type_var.get()
        self._status_label.configure(
            text=f"{report_label}: {len(rows)} record{'s' if len(rows) != 1 else ''}",
        )

        # Store title for exports
        self._current_title = report_label

    # ── Export ───────────────────────────────────────────────

    def _export_pdf(self) -> None:
        """Export current report data to a PDF file."""
        if not self._current_rows:
            messagebox.showinfo(
                "Info", "Generate a report first before exporting.", parent=self,
            )
            return

        filepath = filedialog.asksaveasfilename(
            title="Export as PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"{self._current_report_type}_report.pdf",
        )
        if not filepath:
            return

        success, msg = self._on_export_pdf(
            filepath,
            self._current_headers,
            self._current_rows,
            self._current_title,
            self._current_report_type,
        )
        if success:
            messagebox.showinfo("Success", msg, parent=self)
        else:
            messagebox.showerror("Error", msg, parent=self)

    def _export_excel(self) -> None:
        """Export current report data to an Excel file."""
        if not self._current_rows:
            messagebox.showinfo(
                "Info", "Generate a report first before exporting.", parent=self,
            )
            return

        filepath = filedialog.asksaveasfilename(
            title="Export as Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=f"{self._current_report_type}_report.xlsx",
        )
        if not filepath:
            return

        success, msg = self._on_export_excel(
            filepath,
            self._current_headers,
            self._current_rows,
            self._current_title,
            self._current_report_type,
        )
        if success:
            messagebox.showinfo("Success", msg, parent=self)
        else:
            messagebox.showerror("Error", msg, parent=self)
