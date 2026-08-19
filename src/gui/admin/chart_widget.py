"""Reusable matplotlib chart widget for embedding in Tkinter.

Provides ``AnalyticsChartWidget`` — a frame that wraps a matplotlib
Figure and offers factory methods for bar, line, pie, and horizontal
bar charts commonly used in analytics dashboards.

Rendering failures are handled explicitly instead of silently blanking
the chart area:

* **Unavailable (something is broken)** — the matplotlib import and the
  drawing calls are wrapped in a guard that logs the full exception at
  ERROR level and shows a distinct *unavailable* message in the chart's
  space (e.g. when matplotlib is not installed).  The exception never
  escapes, so the rest of the dashboard keeps rendering.
* **Empty (nothing to show)** — ``show_empty`` renders a centred text
  message with no axes, visually and textually distinct from the
  error state so the two problems can be told apart at a glance.
"""
from __future__ import annotations

import functools
import logging
from typing import Any, Callable, List, Optional

import tkinter as tk
from tkinter import ttk

from src.gui.theme import Theme

logger = logging.getLogger(__name__)

# matplotlib imports are deferred to keep startup fast.  They happen
# lazily inside _init_figure() so a missing matplotlib is caught there
# and surfaced as a clear fallback message instead of propagating
# uncaught (Tkinter would only print it to stderr while the user sees a
# blank area).


def _guard_render(method: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap a chart-drawing method so render failures never escape.

    If the figure cannot be initialised (e.g. matplotlib missing) or
    drawing raises, the error is logged at ERROR level and the widget
    shows its *unavailable* fallback message.  The exception never
    propagates to the caller, so the rest of the dashboard keeps
    rendering even when one chart fails.
    """

    @functools.wraps(method)
    def wrapper(self: "AnalyticsChartWidget", *args: Any, **kwargs: Any) -> Any:
        try:
            if not self._init_figure():
                return
            return method(self, *args, **kwargs)
        except Exception:
            logger.exception(
                "Chart rendering failed in %s — showing fallback",
                method.__name__,
            )
            self.show_unavailable()
            return None

    return wrapper


class AnalyticsChartWidget(ttk.Frame):
    """A tkinter frame embedding a matplotlib chart.

    Typical usage::

        chart = AnalyticsChartWidget(parent, width=5, height=3)
        chart.plot_bar(labels=["A", "B"], values=[10, 20], title="My Chart")
        chart.pack(fill="both", expand=True)
    """

    def __init__(
        self,
        parent: tk.Widget,
        width: int = 6,
        height: int = 3,
        dpi: int = 100,
        **kwargs: Any,
    ) -> None:
        """Initialise the chart widget.

        Args:
            parent: Parent tkinter widget.
            width: Figure width in inches.
            height: Figure height in inches.
            dpi: Figure resolution in dots per inch.
            **kwargs: Extra keyword arguments for ttk.Frame.
        """
        super().__init__(parent, style="TFrame", **kwargs)
        self._width = width
        self._height = height
        self._dpi = dpi
        self._figure: Any = None
        self._axes: Any = None
        self._canvas: Any = None
        self._canvas_widget: Any = None
        # Plain-tk fallback label for the empty / unavailable states.
        # Stays hidden unless show_empty / show_unavailable is called.
        self._fallback = tk.Label(
            self, text="", bg=Theme.SURFACE, fg=Theme.MUTED,
            font=Theme.FONT_BODY, justify="center", wraplength=320,
        )

    # ── Chart types ────────────────────────────────────────────

    @_guard_render
    def plot_bar(
        self,
        labels: List[str],
        values: List[float],
        title: str = "",
        xlabel: str = "",
        ylabel: str = "",
        color: str = "#3498DB",
        rotation: int = 45,
    ) -> None:
        """Draw a vertical bar chart.

        Args:
            labels: Category labels for the x-axis.
            values: Numeric values for each category.
            title: Chart title.
            xlabel: X-axis label.
            ylabel: Y-axis label.
            color: Bar fill colour (hex or named).
            rotation: X-tick label rotation in degrees.
        """
        axes = self._axes
        axes.clear()

        bars = axes.bar(labels, values, color=color, edgecolor="white", linewidth=0.5)
        axes.set_title(title, fontsize=11, fontweight="bold", pad=12)
        axes.set_xlabel(xlabel, fontsize=9)
        axes.set_ylabel(ylabel, fontsize=9)
        axes.tick_params(axis="x", rotation=rotation, labelsize=8)
        axes.tick_params(axis="y", labelsize=8)
        axes.spines["top"].set_visible(False)
        axes.spines["right"].set_visible(False)

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                axes.text(
                    bar.get_x() + bar.get_width() / 2.0, height,
                    f"{int(height)}", ha="center", va="bottom",
                    fontsize=7, fontweight="bold", color=Theme.DARK_TEXT,
                )

        self._refresh()

    @_guard_render
    def plot_line(
        self,
        labels: List[str],
        values: List[float],
        title: str = "",
        xlabel: str = "",
        ylabel: str = "",
        color: str = "#27AE60",
        marker: str = "o",
    ) -> None:
        """Draw a line chart.

        Args:
            labels: X-axis labels (usually dates).
            values: Y-axis values.
            title: Chart title.
            xlabel: X-axis label.
            ylabel: Y-axis label.
            color: Line colour (hex or named).
            marker: Marker style for data points.
        """
        axes = self._axes
        axes.clear()

        axes.plot(labels, values, color=color, marker=marker,
                  linewidth=2, markersize=4, markeredgecolor="white",
                  markeredgewidth=0.5)
        axes.fill_between(range(len(values)), values, alpha=0.1, color=color)
        axes.set_title(title, fontsize=11, fontweight="bold", pad=12)
        axes.set_xlabel(xlabel, fontsize=9)
        axes.set_ylabel(ylabel, fontsize=9)
        axes.tick_params(axis="x", rotation=45, labelsize=8)
        axes.tick_params(axis="y", labelsize=8)
        axes.spines["top"].set_visible(False)
        axes.spines["right"].set_visible(False)
        axes.set_xlim(-0.5, len(labels) - 0.5)

        self._refresh()

    @_guard_render
    def plot_pie(
        self,
        labels: List[str],
        values: List[float],
        title: str = "",
        colors: Optional[List[str]] = None,
    ) -> None:
        """Draw a pie chart.

        Args:
            labels: Slice labels.
            values: Slice sizes.
            title: Chart title.
            colors: Optional list of hex colours.  Defaults to a
                    preset palette if not provided.
        """
        if colors is None:
            colors = ["#3498DB", "#27AE60", "#F39C12", "#E74C3C",
                      "#9B59B6", "#1ABC9C", "#E67E22", "#2ECC71"]

        axes = self._axes
        axes.clear()

        wedges, texts, autotexts = axes.pie(
            values, labels=None, autopct="%1.1f%%",
            colors=colors[:len(values)], startangle=90,
            textprops={"fontsize": 8, "color": Theme.DARK_TEXT},
            wedgeprops={"edgecolor": "white", "linewidth": 1},
        )
        axes.set_title(title, fontsize=11, fontweight="bold", pad=12)

        # Legend outside
        axes.legend(
            wedges, [f"{l} ({int(v)})" for l, v in zip(labels, values)],
            loc="upper left", bbox_to_anchor=(1, 1), fontsize=7,
        )

        self._refresh()

    @_guard_render
    def plot_horizontal_bar(
        self,
        labels: List[str],
        values: List[float],
        title: str = "",
        xlabel: str = "",
        color: str = "#E74C3C",
    ) -> None:
        """Draw a horizontal bar chart (useful for rankings).

        Args:
            labels: Category labels (one per row).
            values: Numeric values.
            title: Chart title.
            xlabel: X-axis label.
            color: Bar fill colour.
        """
        axes = self._axes
        axes.clear()

        y_pos = range(len(labels))
        axes.barh(y_pos, values, color=color, edgecolor="white", linewidth=0.5)
        axes.set_yticks(y_pos)
        axes.set_yticklabels(labels, fontsize=8)
        axes.set_title(title, fontsize=11, fontweight="bold", pad=12)
        axes.set_xlabel(xlabel, fontsize=9)
        axes.tick_params(axis="x", labelsize=8)
        axes.invert_yaxis()
        axes.spines["top"].set_visible(False)
        axes.spines["right"].set_visible(False)

        for i, v in enumerate(values):
            if v > 0:
                axes.text(v + max(values) * 0.01, i, str(int(v)),
                          va="center", fontsize=7, fontweight="bold", color=Theme.DARK_TEXT)

        self._refresh()

    # ── Empty / unavailable states ─────────────────────────────

    def show_empty(self, message: str) -> None:
        """Render a centred empty-state message (no axes drawn).

        Shown when a chart's underlying query returned no rows — "there
        is nothing to show".  Uses a plain tkinter label so it renders
        even if matplotlib is missing, and is visually and textually
        distinct from the error fallback in ``show_unavailable``.

        Args:
            message: Empty-state text (e.g. "No appointments in this
                date range").
        """
        self._clear_canvas()
        self._fallback.configure(
            text=message, fg=Theme.MUTED,
            font=Theme.FONT_BODY, bg=Theme.SURFACE,
        )
        self._fallback.pack(fill="both", expand=True)

    def show_unavailable(self, message: str = "Chart rendering unavailable") -> None:
        """Render an error fallback (e.g. matplotlib not installed).

        Distinct from ``show_empty``: this signals that something is
        broken (missing dependency, render error), not that there is
        simply nothing to show.

        Args:
            message: Error text shown in the chart's space.
        """
        self._clear_canvas()
        self._fallback.configure(
            text=message, fg=Theme.DANGER,
            font=Theme.FONT_SMALL_BOLD, bg=Theme.SURFACE,
        )
        self._fallback.pack(fill="both", expand=True)

    def _clear_canvas(self) -> None:
        """Remove any matplotlib canvas and hide the fallback label."""
        if self._canvas_widget is not None:
            self._canvas_widget.destroy()
            self._canvas_widget = None
        self._fallback.pack_forget()

    # ─── Utilities ────────────────────────────────────────────

    def get_figure(self) -> Any:
        """Return the underlying matplotlib Figure (for saving to file).

        Returns:
            The matplotlib Figure object, or None if rendering is
            unavailable.
        """
        if self._figure is None:
            if not self._init_figure():
                return None
        return self._figure

    def save_figure(self, filepath: str, dpi: int = 150) -> None:
        """Save the current chart to an image file.

        Args:
            filepath: Destination file path (e.g. /tmp/chart.png).
            dpi: Output resolution.
        """
        if self._figure is not None:
            self._figure.tight_layout()
            self._figure.savefig(filepath, dpi=dpi, bbox_inches="tight")

    def clear(self) -> None:
        """Clear the chart area."""
        if self._axes is not None:
            self._axes.clear()
            self._refresh()

    # ── Internal helpers ──────────────────────────────────────

    def _init_figure(self) -> bool:
        """Lazily initialise the matplotlib figure and canvas.

        Returns:
            True when the figure is ready, False when rendering is
            unavailable — in which case a clear fallback message is
            shown in the widget's space instead of a silent blank area.
        """
        if self._figure is not None:
            return True

        try:
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.figure import Figure
        except Exception:
            logger.exception(
                "Chart rendering unavailable — matplotlib import failed; "
                "install with: pip install -r requirements.txt",
            )
            self.show_unavailable(
                "Chart rendering unavailable — missing dependency",
            )
            return False

        try:
            self._figure = Figure(figsize=(self._width, self._height), dpi=self._dpi)
            self._figure.set_facecolor(Theme.SURFACE)
            self._axes = self._figure.add_subplot(111)
            self._apply_theme_colors()

            self._canvas = FigureCanvasTkAgg(self._figure, master=self)
            self._canvas_widget = self._canvas.get_tk_widget()
            self._canvas_widget.pack(fill="both", expand=True)
            return True
        except Exception:
            logger.exception("Chart rendering unavailable — figure initialisation failed")
            self._figure = None
            self._axes = None
            self._canvas = None
            self.show_unavailable()
            return False

    def _apply_theme_colors(self) -> None:
        """Match axes text/spines to the current theme palette."""
        if self._axes is None:
            return
        axes = self._axes
        axes.set_facecolor(Theme.SURFACE)
        axes.title.set_color(Theme.DARK_TEXT)
        axes.xaxis.label.set_color(Theme.DARK_TEXT)
        axes.yaxis.label.set_color(Theme.DARK_TEXT)
        axes.tick_params(colors=Theme.DARK_TEXT, which="both")
        for spine in axes.spines.values():
            spine.set_color(Theme.BORDER)
        if axes.get_legend():
            axes.get_legend().get_frame().set_facecolor(Theme.SURFACE)
            axes.get_legend().get_frame().set_edgecolor(Theme.BORDER)
            for text in axes.get_legend().get_texts():
                text.set_color(Theme.DARK_TEXT)

    def _refresh(self) -> None:
        """Redraw the canvas."""
        if self._canvas is not None:
            self._figure.tight_layout()
            self._canvas.draw_idle()
