"""Analytics Dashboard — full-screen charts and export for administrators.

Hosts 6 interactive matplotlib charts with a date-range filter bar
and PDF / Excel export buttons for the entire dashboard.
"""
from __future__ import annotations

import logging
import os
from datetime import date, timedelta, datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from src.gui.theme import Theme
from src.gui.common.base_view import BaseView
from src.gui.admin.chart_widget import AnalyticsChartWidget
from src.utils.formatters import format_date, parse_date_for_input, DISPLAY_DATE_FORMAT
from src.services.export_service import (
    export_analytics_pdf,
    export_analytics_excel,
)

logger = logging.getLogger(__name__)


class AnalyticsDashboardView(BaseView):
    """Full analytics dashboard with 6 charts and export functionality.

    Charts
    ------
    1. Appointments per day    (bar chart)
    2. Patients per day        (bar chart)
    3. Doctor workload         (horizontal bar)
    4. Department statistics   (pie chart)
    5. Cancellation rate       (line chart)
    6. Peak hours              (bar chart)

    Export
    ------
    * PDF — saves a multi-page PDF with all charts
    * Excel — saves tabular data to an .xlsx workbook
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_load_data: Callable[[date, date], Dict[str, Any]],
        on_export_pdf: Callable[[date, date, str], Tuple[bool, str]],
        on_export_excel: Callable[[date, date, str], Tuple[bool, str]],
        **kwargs: Any,
    ) -> None:
        """Initialise the analytics dashboard.

        Args:
            parent: Parent tkinter widget.
            on_load_data: Callback(start, end) → analytics data dict.
            on_export_pdf: Callback(start, end, filepath) → (success, msg).
            on_export_excel: Callback(start, end, filepath) → (success, msg).
            **kwargs: Extra keyword arguments for BaseView.
        """
        super().__init__(parent, **kwargs)
        self._on_load_data = on_load_data
        self._on_export_pdf = on_export_pdf
        self._on_export_excel = on_export_excel

        # Default date range: last 30 days
        self._end_date = date.today()
        self._start_date = self._end_date - timedelta(days=30)

        self._data: Dict[str, Any] = {}
        self._charts: List[AnalyticsChartWidget] = []

        self._build_ui()
        self._load_data()

    def _build_ui(self) -> None:
        """Construct the dashboard layout."""
        # ── Header ─────────────────────────────────────────────
        header = ttk.Frame(self, style="Header.TFrame", padding=16)
        header.pack(fill="x")

        ttk.Label(header, text="Analytics Dashboard", style="Heading.TLabel").pack(side="left")
        ttk.Label(header, text="  |  Visual insights & reports", style="Subheading.TLabel").pack(side="left", padx=(8, 0))

        # ── Date range filter bar ──────────────────────────────
        filter_frame = ttk.Frame(self, style="TFrame", padding=(16, 8))
        filter_frame.pack(fill="x")

        ttk.Label(filter_frame, text="From:", font=Theme.FONT_BODY).pack(side="left", padx=(0, 4))
        self._start_var = tk.StringVar(value=format_date(self._start_date))
        start_entry = ttk.Entry(filter_frame, textvariable=self._start_var, width=12, font=Theme.FONT_BODY)
        start_entry.pack(side="left", padx=(0, 12))

        ttk.Label(filter_frame, text="To:", font=Theme.FONT_BODY).pack(side="left", padx=(0, 4))
        self._end_var = tk.StringVar(value=format_date(self._end_date))
        end_entry = ttk.Entry(filter_frame, textvariable=self._end_var, width=12, font=Theme.FONT_BODY)
        end_entry.pack(side="left", padx=(0, 12))

        # Quick date range buttons
        for label, days_back in [("Last 7 Days", 7), ("Last 30 Days", 30), ("Last 90 Days", 90), ("This Year", 365)]:
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

        # Export buttons
        tk.Button(
            filter_frame, text="📄 Export PDF", bg=Theme.DANGER, fg=Theme.WHITE,
            font=Theme.FONT_SMALL_BOLD, cursor="hand2", bd=0, padx=10, pady=3,
            command=self._export_pdf,
        ).pack(side="right", padx=(0, 4))

        tk.Button(
            filter_frame, text="📊 Export Excel", bg=Theme.SUCCESS, fg=Theme.WHITE,
            font=Theme.FONT_SMALL_BOLD, cursor="hand2", bd=0, padx=10, pady=3,
            command=self._export_excel,
        ).pack(side="right", padx=(0, 8))

        # ── Scrollable chart grid ──────────────────────────────
        self._canvas_frame = tk.Canvas(self, bg=Theme.BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self._canvas_frame.yview)
        self._chart_container = ttk.Frame(self._canvas_frame, style="TFrame")
        self._chart_container.bind(
            "<Configure>",
            lambda e: self._canvas_frame.configure(scrollregion=self._canvas_frame.bbox("all")),
        )
        self._canvas_frame.create_window((0, 0), window=self._chart_container, anchor="nw")
        self._canvas_frame.configure(yscrollcommand=scrollbar.set)

        self._canvas_frame.pack(side="left", fill="both", expand=True, padx=16, pady=(0, 16))
        scrollbar.pack(side="right", fill="y")

        # Chart grid: 2 columns × 3 rows
        self._chart_container.columnconfigure(0, weight=1, uniform="chart")
        self._chart_container.columnconfigure(1, weight=1, uniform="chart")

    # ── Data loading ──────────────────────────────────────────

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
        """Parse date inputs and fetch analytics data."""
        self._start_date = parse_date_for_input(self._start_var.get().strip())
        self._end_date = parse_date_for_input(self._end_var.get().strip())
        if self._start_date is None or self._end_date is None:
            messagebox.showwarning("Warning", f"Invalid date format. Use {DISPLAY_DATE_FORMAT}.", parent=self)
            return

        if self._start_date > self._end_date:
            messagebox.showwarning("Warning", "Start date must be before end date.", parent=self)
            return

        self._data = self._on_load_data(self._start_date, self._end_date)
        self._render_charts()

    def _render_charts(self) -> None:
        """Render all 6 charts into the grid.

        Each chart is rendered independently: a failure in one (bad
        data shape, missing matplotlib, etc.) logs the error and shows
        that chart's fallback message while the others still render.
        """
        # Clear existing charts
        for widget in self._chart_container.winfo_children():
            widget.destroy()
        self._charts.clear()

        data = self._data

        # 1. Appointments per day (bar)
        chart1 = AnalyticsChartWidget(self._chart_container, width=5.5, height=3)
        chart1.grid(row=0, column=0, padx=6, pady=6, sticky="nsew")
        self._charts.append(chart1)
        try:
            daily = data.get("daily_appointments", {}).get("daily_counts", [])
            if daily:
                labels = [str(d.get("appointment_date", ""))[-5:] for d in daily]
                values = [d.get("count", 0) for d in daily]
                chart1.plot_bar(labels, values, title="Appointments per Day",
                                xlabel="Date", ylabel="Count", color=Theme.ACCENT)
            else:
                chart1.show_empty("No appointments in this date range")
        except Exception:
            logger.exception("Chart 1 (Appointments per Day) failed to render")
            chart1.show_unavailable()

        # 2. Patients per day (bar)
        chart2 = AnalyticsChartWidget(self._chart_container, width=5.5, height=3)
        chart2.grid(row=0, column=1, padx=6, pady=6, sticky="nsew")
        self._charts.append(chart2)
        try:
            registrations = data.get("patient_registrations", [])
            if registrations:
                labels = [str(r.get("registration_date", ""))[-5:] for r in registrations]
                values = [r.get("count", 0) for r in registrations]
                chart2.plot_bar(labels, values, title="Patients Registered per Day",
                                xlabel="Date", ylabel="Count", color=Theme.SUCCESS)
            else:
                chart2.show_empty("No patients registered in this date range")
        except Exception:
            logger.exception("Chart 2 (Patients Registered per Day) failed to render")
            chart2.show_unavailable()

        # 3. Doctor workload (horizontal bar)
        chart3 = AnalyticsChartWidget(self._chart_container, width=5.5, height=3)
        chart3.grid(row=1, column=0, padx=6, pady=6, sticky="nsew")
        self._charts.append(chart3)
        try:
            workload = data.get("doctor_workload", [])
            if workload:
                labels = [d.get("doctor_name", "Unknown")[:20] for d in workload[:10]]
                values = [d.get("appointment_count", 0) for d in workload[:10]]
                chart3.plot_horizontal_bar(labels, values, title="Doctor Workload",
                                           xlabel="Appointments", color=Theme.WARNING)
            else:
                chart3.show_empty("No appointment data for doctors")
        except Exception:
            logger.exception("Chart 3 (Doctor Workload) failed to render")
            chart3.show_unavailable()

        # 4. Department statistics (pie)
        chart4 = AnalyticsChartWidget(self._chart_container, width=5.5, height=3)
        chart4.grid(row=1, column=1, padx=6, pady=6, sticky="nsew")
        self._charts.append(chart4)
        try:
            dept_stats = data.get("department_stats", [])
            if dept_stats:
                labels = [d.get("department_name", "Unknown") for d in dept_stats]
                values = [d.get("count", 0) for d in dept_stats]
                chart4.plot_pie(labels, values, title="Appointments by Department")
            else:
                chart4.show_empty("No appointment data by department")
        except Exception:
            logger.exception("Chart 4 (Appointments by Department) failed to render")
            chart4.show_unavailable()

        # 5. Cancellation rate (line)
        chart5 = AnalyticsChartWidget(self._chart_container, width=5.5, height=3)
        chart5.grid(row=2, column=0, padx=6, pady=6, sticky="nsew")
        self._charts.append(chart5)
        try:
            cancel_data = data.get("cancellation_rate", [])
            if cancel_data:
                labels = [str(c.get("appointment_date", ""))[-5:] for c in cancel_data]
                values = [c.get("rate", 0) for c in cancel_data]
                chart5.plot_line(labels, values, title="Cancellation Rate (%)",
                                 xlabel="Date", ylabel="Rate %", color=Theme.DANGER)
            else:
                chart5.show_empty("No appointment data in this date range")
        except Exception:
            logger.exception("Chart 5 (Cancellation Rate) failed to render")
            chart5.show_unavailable()

        # 6. Peak hours (bar)
        chart6 = AnalyticsChartWidget(self._chart_container, width=5.5, height=3)
        chart6.grid(row=2, column=1, padx=6, pady=6, sticky="nsew")
        self._charts.append(chart6)
        try:
            peak = data.get("peak_hours", [])
            if peak:
                labels = [f"{int(p.get('hour', 0)):02d}:00" for p in peak]
                values = [p.get("count", 0) for p in peak]
                chart6.plot_bar(labels, values, title="Peak Hours (Appointments by Hour)",
                                xlabel="Hour of Day", ylabel="Appointments",
                                color="#9B59B6", rotation=0)
            else:
                chart6.show_empty("No appointment data by hour")
        except Exception:
            logger.exception("Chart 6 (Peak Hours) failed to render")
            chart6.show_unavailable()

    # ── Export ─────────────────────────────────────────────────

    def _export_pdf(self) -> None:
        """Export the dashboard to a PDF file."""
        filepath = filedialog.asksaveasfilename(
            title="Export as PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"analytics_{self._start_date}_to_{self._end_date}.pdf",
        )
        if not filepath:
            return

        # Save chart snapshots and pass them through for embedding
        chart_paths = self._save_chart_snapshots()

        success, msg = self._on_export_pdf(
            self._start_date, self._end_date, filepath, chart_paths,
        )
        if success:
            messagebox.showinfo("Success", msg, parent=self)
        else:
            messagebox.showerror("Error", msg, parent=self)

    def _export_excel(self) -> None:
        """Export tabular data to an Excel file."""
        filepath = filedialog.asksaveasfilename(
            title="Export as Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=f"analytics_{self._start_date}_to_{self._end_date}.xlsx",
        )
        if not filepath:
            return

        success, msg = self._on_export_excel(
            self._start_date, self._end_date, filepath,
        )
        if success:
            messagebox.showinfo("Success", msg, parent=self)
        else:
            messagebox.showerror("Error", msg, parent=self)

    def _save_chart_snapshots(self) -> List[str]:
        """Save each chart as a PNG and return the file paths.

        Returns:
            List of temporary PNG file paths.
        """
        paths = []
        for idx, chart in enumerate(self._charts):
            path = os.path.join("/tmp", f"chart_{idx}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png")
            chart.save_figure(path)
            paths.append(path)
        return paths


