"""Tests for chart-widget rendering fallbacks and the startup dependency check.

Covers the regression class fixed around the analytics dashboard:

* ``AnalyticsChartWidget`` must never let a render failure (e.g. missing
  matplotlib) escape silently — it logs at ERROR level and shows a
  distinct *unavailable* message instead of a blank area.
* Empty data shows a distinct *empty* message (not an error), so the
  two states can be told apart.
* A single failing chart must not stop the other charts from rendering.
* ``check_critical_dependencies`` warns at startup when a critical
  package is missing.

GUI tests need a display; they skip automatically when Tk cannot start.
"""
from __future__ import annotations

import logging
import sys
from unittest.mock import patch

import pytest

from src.app import CRITICAL_DEPENDENCIES, check_critical_dependencies


@pytest.fixture
def tk_root():
    """Create a real Tk root; skip tests when no display is available."""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
    except Exception as exc:  # pragma: no cover - depends on environment
        pytest.skip(f"Tk display unavailable: {exc}")
    yield root
    try:
        root.destroy()
    except Exception:
        pass


@pytest.fixture
def chart(tk_root):
    """A fresh AnalyticsChartWidget in the test root."""
    from src.gui.admin.chart_widget import AnalyticsChartWidget
    widget = AnalyticsChartWidget(tk_root, width=4, height=2)
    yield widget
    widget.destroy()


# ── Normal rendering ───────────────────────────────────────────


class TestRendering:
    """With matplotlib present, charts draw real figures."""

    def test_plot_bar_creates_figure(self, chart) -> None:
        """A bar chart with data produces a figure, no fallback shown."""
        chart.plot_bar(["A", "B"], [1, 2], title="Test")
        assert chart._figure is not None
        assert chart._axes is not None
        assert not chart._fallback.winfo_manager()

    def test_plot_pie_creates_figure(self, chart) -> None:
        """A pie chart with data produces a figure."""
        chart.plot_pie(["A", "B"], [1, 2], title="Pie")
        assert chart._figure is not None

    def test_plot_line_creates_figure(self, chart) -> None:
        """A line chart with data produces a figure."""
        chart.plot_line(["A"], [1], title="Line")
        assert chart._figure is not None


# ── Unavailable (missing dependency) state ─────────────────────


class TestUnavailableState:
    """A render failure must be visible and logged, never silent."""

    def test_missing_matplotlib_shows_unavailable(self, chart, caplog) -> None:
        """Simulate matplotlib being unimportable: fallback + ERROR log."""
        with patch.dict(sys.modules, {"matplotlib": None}):
            with caplog.at_level(logging.ERROR, logger="src.gui.admin.chart_widget"):
                chart.plot_bar(["A"], [1], title="Test")

        # No figure was created…
        assert chart._figure is None
        # …the fallback label is shown with a distinct unavailable
        # message (import failure → "missing dependency"; cached-submodule
        # failure → "Chart rendering unavailable" — both are the error
        # state, distinct from the empty-state wording)…
        assert chart._fallback.winfo_manager()
        assert "unavailable" in chart._fallback.cget("text").lower()
        # …and the failure was logged, not swallowed silently.
        assert "matplotlib" in caplog.text
        assert "ERROR" in caplog.text or "exception" in caplog.text.lower()

    def test_render_exception_shows_unavailable(self, chart, caplog) -> None:
        """A non-import render failure also shows the fallback."""

        def boom(*args, **kwargs):
            raise RuntimeError("simulated draw failure")

        with patch.object(chart, "_refresh", side_effect=boom):
            with caplog.at_level(logging.ERROR, logger="src.gui.admin.chart_widget"):
                chart.plot_bar(["A"], [1], title="Test")

        assert chart._fallback.winfo_manager()
        assert "unavailable" in chart._fallback.cget("text").lower()
        assert "simulated draw failure" in caplog.text

    def test_unavailable_exception_never_escapes(self, chart) -> None:
        """plot_* must not raise even when rendering is broken."""
        with patch.dict(sys.modules, {"matplotlib": None}):
            # Should not raise.
            chart.plot_bar(["A"], [1], title="Test")
            chart.plot_pie(["A"], [1], title="Test")


# ── Empty (no data) state ──────────────────────────────────────


class TestEmptyState:
    """Empty data shows a clear message, distinct from the error state."""

    def test_show_empty_uses_distinct_message(self, chart) -> None:
        """show_empty shows centred text, not an error and not a chart."""
        chart.show_empty("No appointments in this date range")
        assert chart._fallback.winfo_manager()
        assert chart._fallback.cget("text") == "No appointments in this date range"
        # Not the error wording.
        assert "unavailable" not in chart._fallback.cget("text").lower()
        # No axes drawn for an empty state.
        assert chart._figure is None

    def test_empty_and_unavailable_are_textually_distinct(self, chart) -> None:
        """The two fallbacks are distinguishable by message."""
        chart.show_empty("No data")
        empty_text = chart._fallback.cget("text")
        chart.show_unavailable()
        error_text = chart._fallback.cget("text")
        assert empty_text != error_text
        assert "unavailable" in error_text.lower()
        assert "unavailable" not in empty_text.lower()


# ── Analytics dashboard: one failure must not kill the rest ────


class TestDashboardIsolation:
    """A single chart failing must not stop the other five."""

    def test_one_bad_chart_does_not_block_others(self, tk_root) -> None:
        """A malformed dataset for one chart shows fallback; others render."""
        from src.gui.theme import Theme
        Theme.configure_ttk()
        from src.gui.admin.analytics_dashboard_view import AnalyticsDashboardView

        # chart6 (peak hours) gets a None hour → int(None) raises in the
        # view's data-shaping step; every other chart gets good data.
        def fake_load(start, end):
            return {
                "daily_appointments": {
                    "daily_counts": [{"appointment_date": "2026-07-30", "count": 6}],
                },
                "patient_registrations": [
                    {"registration_date": "2026-07-30", "count": 8},
                ],
                "doctor_workload": [
                    {"doctor_name": "Dr. A", "appointment_count": 3},
                ],
                "department_stats": [{"department_name": "Cardio", "count": 3}],
                "cancellation_rate": [
                    {"appointment_date": "2026-07-30", "rate": 16.7},
                ],
                "peak_hours": [{"hour": None, "count": 1}],  # deliberately broken
            }

        view = AnalyticsDashboardView(
            tk_root,
            on_load_data=fake_load,
            on_export_pdf=lambda *a: (True, "ok"),
            on_export_excel=lambda *a: (True, "ok"),
        )

        assert len(view._charts) == 6
        rendered = [c for c in view._charts if c._figure is not None]
        fallbacks = [c for c in view._charts if c._fallback.winfo_manager()]
        # The five good charts rendered; only the broken one shows a fallback.
        assert len(rendered) == 5
        assert len(fallbacks) == 1
        assert "unavailable" in fallbacks[0]._fallback.cget("text").lower()
        view.destroy()


# ── Startup dependency check ───────────────────────────────────


class TestDependencyCheck:
    """check_critical_dependencies warns (non-blocking) on missing deps."""

    def test_warns_when_dependency_missing(self, caplog) -> None:
        """A missing module logs a clear WARNING naming the consequence."""
        with patch(
            "importlib.import_module",
            side_effect=lambda name: (_ for _ in ()).throw(
                ImportError(f"No module named {name!r}")
            ),
        ):
            with caplog.at_level(logging.WARNING, logger="app"):
                check_critical_dependencies()
        assert "matplotlib" in caplog.text
        assert "will not render" in caplog.text
        assert "install" in caplog.text.lower()

    def test_no_warning_when_all_present(self, caplog) -> None:
        """With everything importable there is nothing to warn about."""
        with caplog.at_level(logging.WARNING, logger="app"):
            check_critical_dependencies()
        assert "Missing dependency" not in caplog.text

    def test_covers_critical_packages(self) -> None:
        """The check must include the analytics chart stack."""
        names = {m for m, _ in CRITICAL_DEPENDENCIES}
        assert "matplotlib" in names
        assert "numpy" in names
        assert "mysql.connector" in names
