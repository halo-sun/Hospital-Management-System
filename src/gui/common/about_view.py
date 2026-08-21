"""About / Credits page for the Hospital Management System.

A static, read-only view displaying project info, team members,
and copyright details.  Designed to be visually polished and fully
compatible with both light and dark themes.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import List, Tuple

from src.config import app_config
from src.gui.theme import Theme


# ── Team data ────────────────────────────────────────────────

TEAM_MEMBERS: List[Tuple[str, str, str]] = [
    ("DS", "Dharshan Srinath S", "192521216"),
    ("GK", "G M Karl Siddharth", "192512083"),
    ("NM", "Nishanth M", "192420020"),
]


# ── Helpers ──────────────────────────────────────────────────


def _make_card(
    parent: tk.Widget,
    bg: str,
    border_color: str,
    padx: int = 0,
    pady: int = 0,
) -> tk.Frame:
    """Return a styled card frame with a subtle border."""
    outer = tk.Frame(parent, bg=bg, bd=0, highlightthickness=1,
                     highlightbackground=border_color, highlightcolor=border_color)
    outer.pack(padx=padx, pady=pady, fill="x")
    inner = tk.Frame(outer, bg=bg, padx=20, pady=14)
    inner.pack(fill="x")
    return inner


def _initials_circle(
    parent: tk.Widget,
    initials: str,
    size: int = 56,
) -> tk.Canvas:
    """Draw a circle with initials inside (accent background, white text)."""
    canvas = tk.Canvas(
        parent, width=size, height=size,
        bg=Theme.SURFACE, highlightthickness=0,
    )
    r = size // 2
    canvas.create_oval(2, 2, size - 2, size - 2, fill=Theme.ACCENT, outline="")
    canvas.create_text(
        r, r, text=initials, fill=Theme.WHITE,
        font=(Theme.FONT_FAMILY, 16, "bold"),
    )
    return canvas


# ── View ─────────────────────────────────────────────────────


class AboutView(tk.Frame):
    """Static About / Credits page."""

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, bg=Theme.BG)

        # Scrollable outer wrapper
        canvas = tk.Canvas(self, bg=Theme.BG, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self._scroll_frame = tk.Frame(canvas, bg=Theme.BG)

        self._scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self._scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mouse-wheel scrolling (cross-platform)
        def _on_mousewheel(event: tk.Event) -> None:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_mousewheel_linux(event: tk.Event) -> None:
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

        canvas.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Button-4>", _on_mousewheel_linux)
        canvas.bind("<Button-5>", _on_mousewheel_linux)

        # Centre the content column
        center = tk.Frame(self._scroll_frame, bg=Theme.BG)
        center.pack(expand=True, fill="x", padx=60, pady=40)

        self._build_header(center)
        self._build_project_card(center)
        self._build_team_section(center)
        self._build_footer(center)

    # ── Header ────────────────────────────────────────────────

    def _build_header(self, parent: tk.Widget) -> None:
        frame = tk.Frame(parent, bg=Theme.BG)
        frame.pack(fill="x", pady=(0, 28))

        # App icon (reuse assets/icon.png)
        try:
            _icon_path = app_config.ASSETS_DIR + "/icon.png"
            self._icon_image = tk.PhotoImage(file=_icon_path)
            # Scale down if too large (icon.png may be big)
            if self._icon_image.width() > 80:
                self._icon_image = self._icon_image.subsample(
                    self._icon_image.width() // 80,
                    self._icon_image.height() // 80,
                )
            tk.Label(frame, image=self._icon_image, bg=Theme.BG).pack(
                pady=(0, 12),
            )
        except Exception:
            # Fallback: large emoji icon
            tk.Label(
                frame, text="🏥", bg=Theme.BG, fg=Theme.ACCENT,
                font=(Theme.FONT_FAMILY, 48),
            ).pack(pady=(0, 12))

        tk.Label(
            frame, text=app_config.NAME, bg=Theme.BG, fg=Theme.HEADING,
            font=(Theme.FONT_FAMILY, 22, "bold"),
        ).pack()

        tk.Label(
            frame, text=f"Version {app_config.VERSION}", bg=Theme.BG,
            fg=Theme.ACCENT, font=Theme.FONT_SUBHEADING,
        ).pack(pady=(4, 0))

        tk.Label(
            frame,
            text="A centralized hospital scheduling and patient management system",
            bg=Theme.BG, fg=Theme.MUTED, font=Theme.FONT_SMALL,
        ).pack(pady=(8, 0))

    # ── Project info card ─────────────────────────────────────

    def _build_project_card(self, parent: tk.Widget) -> None:
        card = _make_card(parent, Theme.SURFACE, Theme.BORDER, pady=(0, 20))

        tk.Label(
            card, text="Capstone Project", bg=Theme.SURFACE,
            fg=Theme.HEADING, font=Theme.FONT_SUBHEADING,
        ).pack(anchor="w")

        tk.Label(
            card, text="CSA0801: Python Programming", bg=Theme.SURFACE,
            fg=Theme.DARK_TEXT, font=Theme.FONT_BODY,
        ).pack(anchor="w", pady=(2, 8))

        sep = tk.Frame(card, bg=Theme.BORDER, height=1)
        sep.pack(fill="x", pady=(0, 8))

        tk.Label(
            card, text="Guided by", bg=Theme.SURFACE,
            fg=Theme.MUTED, font=Theme.FONT_SMALL,
        ).pack(anchor="w")

        tk.Label(
            card, text="Dr. S. Sankar", bg=Theme.SURFACE,
            fg=Theme.DARK_TEXT, font=Theme.FONT_BODY_BOLD,
        ).pack(anchor="w", pady=(2, 0))

    # ── Team section ──────────────────────────────────────────

    def _build_team_section(self, parent: tk.Widget) -> None:
        tk.Label(
            parent, text="Developed By", bg=Theme.BG, fg=Theme.HEADING,
            font=Theme.FONT_HEADING,
        ).pack(anchor="w", pady=(0, 14))

        # Three cards in a row (wraps on narrow windows)
        row = tk.Frame(parent, bg=Theme.BG)
        row.pack(fill="x", pady=(0, 20))

        # Use grid for equal distribution
        for i in range(3):
            row.columnconfigure(i, weight=1, uniform="team")

        for idx, (initials, name, reg_no) in enumerate(TEAM_MEMBERS):
            card_outer = tk.Frame(
                row, bg=Theme.SURFACE, bd=0, highlightthickness=1,
                highlightbackground=Theme.BORDER, highlightcolor=Theme.BORDER,
            )
            card_outer.grid(row=0, column=idx, padx=6, pady=4, sticky="nsew")

            card = tk.Frame(card_outer, bg=Theme.SURFACE, padx=16, pady=18)
            card.pack(fill="both", expand=True)

            _initials_circle(card, initials, size=56).pack(pady=(0, 10))

            tk.Label(
                card, text=name, bg=Theme.SURFACE, fg=Theme.HEADING,
                font=Theme.FONT_BODY_BOLD, wraplength=180,
            ).pack()

            tk.Label(
                card, text=f"Reg. No. {reg_no}", bg=Theme.SURFACE,
                fg=Theme.MUTED, font=Theme.FONT_SMALL,
            ).pack(pady=(4, 0))

    # ── Footer ────────────────────────────────────────────────

    def _build_footer(self, parent: tk.Widget) -> None:
        sep = tk.Frame(parent, bg=Theme.BORDER, height=1)
        sep.pack(fill="x", pady=(0, 14))

        tk.Label(
            parent,
            text=f"© {app_config.COPYRIGHT}. All rights reserved.",
            bg=Theme.BG, fg=Theme.MUTED, font=Theme.FONT_SMALL,
        ).pack(anchor="w")

        tk.Label(
            parent,
            text="Built with Python  ·  Tkinter  ·  MySQL",
            bg=Theme.BG, fg=Theme.MUTED,
            font=(Theme.FONT_FAMILY, 9),
        ).pack(anchor="w", pady=(4, 0))
