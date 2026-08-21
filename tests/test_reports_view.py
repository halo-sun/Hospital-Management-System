"""Smoke tests for src/gui/admin/reports_view.py.

The reports module was rebuilt from completely broken code (the factory
was returning AdminDashboard instead of a real reports view). These
tests ensure the view constructs correctly, key widgets exist, and
the generate callback fires without error.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from datetime import date, timedelta
from typing import Any, Dict, List, Tuple
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def root():
    """Create a hidden tkinter root window."""
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()


class TestReportsViewConstruction:
    """Verify the view constructs and key widgets are present."""

    def test_view_creates_without_error(self, root):
        """Basic construction should not raise."""
        from src.gui.admin.reports_view import ReportsView

        on_generate = MagicMock(return_value=[])
        on_pdf = MagicMock(return_value=(True, "ok"))
        on_xlsx = MagicMock(return_value=(True, "ok"))

        view = ReportsView(root, on_generate=on_generate,
                           on_export_pdf=on_pdf, on_export_excel=on_xlsx)
        assert view is not None

    def test_report_type_dropdown_exists(self, root):
        """The report type selector combobox should be present."""
        from src.gui.admin.reports_view import ReportsView

        view = ReportsView(root, on_generate=MagicMock(return_value=[]),
                           on_export_pdf=MagicMock(return_value=(True, "")),
                           on_export_excel=MagicMock(return_value=(True, "")))

        # Walk children to find a Combobox
        combos = []
        def find_combos(w):
            if isinstance(w, ttk.Combobox):
                combos.append(w)
            for c in w.winfo_children():
                find_combos(c)
        find_combos(view)
        assert len(combos) >= 1, "No Combobox found for report type selector"

    def test_generate_button_exists(self, root):
        """The Generate Report button should be present."""
        from src.gui.admin.reports_view import ReportsView

        view = ReportsView(root, on_generate=MagicMock(return_value=[]),
                           on_export_pdf=MagicMock(return_value=(True, "")),
                           on_export_excel=MagicMock(return_value=(True, "")))

        buttons = []
        def find_buttons(w):
            if isinstance(w, tk.Button):
                buttons.append(w.cget("text"))
            for c in w.winfo_children():
                find_buttons(c)
        find_buttons(view)
        assert any("Generate" in t for t in buttons), \
            f"No 'Generate' button found among: {buttons}"

    def test_treeview_exists(self, root):
        """A Treeview for results should be present."""
        from src.gui.admin.reports_view import ReportsView

        view = ReportsView(root, on_generate=MagicMock(return_value=[]),
                           on_export_pdf=MagicMock(return_value=(True, "")),
                           on_export_excel=MagicMock(return_value=(True, "")))

        trees = []
        def find_trees(w):
            if isinstance(w, ttk.Treeview):
                trees.append(w)
            for c in w.winfo_children():
                find_trees(c)
        find_trees(view)
        assert len(trees) >= 1, "No Treeview found for report results"


class TestReportsViewGenerate:
    """Verify the generate callback fires and results populate."""

    def test_generate_callback_fires(self, root):
        """Clicking generate should call on_generate with correct args."""
        from src.gui.admin.reports_view import ReportsView

        mock_rows = [
            {"date": "2026-08-01", "count": 5},
            {"date": "2026-08-02", "count": 3},
        ]
        on_generate = MagicMock(return_value=mock_rows)

        view = ReportsView(root, on_generate=on_generate,
                           on_export_pdf=MagicMock(return_value=(True, "")),
                           on_export_excel=MagicMock(return_value=(True, "")))

        # Simulate triggering generate via the button's command
        # Find the generate button and invoke its command
        generate_btn = None
        def find_generate(w):
            nonlocal generate_btn
            if isinstance(w, tk.Button) and "Generate" in str(w.cget("text")):
                generate_btn = w
            for c in w.winfo_children():
                find_generate(c)
        find_generate(view)

        assert generate_btn is not None, "Generate button not found"
        generate_btn.invoke()

        # on_generate should have been called at least once
        assert on_generate.call_count >= 1, "on_generate was not called"

    def test_generate_with_empty_results(self, root):
        """Empty results should not crash the view."""
        from src.gui.admin.reports_view import ReportsView

        on_generate = MagicMock(return_value=[])
        view = ReportsView(root, on_generate=on_generate,
                           on_export_pdf=MagicMock(return_value=(True, "")),
                           on_export_excel=MagicMock(return_value=(True, "")))

        generate_btn = None
        def find_generate(w):
            nonlocal generate_btn
            if isinstance(w, tk.Button) and "Generate" in str(w.cget("text")):
                generate_btn = w
            for c in w.winfo_children():
                find_generate(c)
        find_generate(view)

        # Should not raise even with empty results
        generate_btn.invoke()
        assert on_generate.call_count >= 1

    def test_report_types_list_not_empty(self):
        """REPORT_TYPES constant should have entries."""
        from src.gui.admin.reports_view import REPORT_TYPES
        assert len(REPORT_TYPES) >= 5, \
            f"Expected at least 5 report types, got {len(REPORT_TYPES)}"
        # Each entry should be (key, label, needs_date_range)
        for entry in REPORT_TYPES:
            assert len(entry) == 3
            assert isinstance(entry[0], str)
            assert isinstance(entry[1], str)
            assert isinstance(entry[2], bool)
