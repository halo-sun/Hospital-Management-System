"""Theme constants and styling for the Tkinter GUI.

Provides a professional hospital-inspired colour palette and
comprehensive ttk style configuration used by every view in
the application.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import ClassVar, List
from src.config import app_config


class Theme:
    """Centralised colour, font, and style definitions.

    All widgets should reference these constants so that the look
    stays consistent across every screen.  Change values here to
    rebrand the entire application.
    """

    # ── Theming ────────────────────────────────────────────────
    # Two named palettes: "flatly" (light, default) and "darkly".
    # ``apply_theme`` swaps the class attributes below and re-runs
    # ``configure_ttk`` so every view reflects the change immediately.
    THEMES = {
        "flatly": {
            # Primary palette – sober medical blues
            "PRIMARY": "#1B2A4A",          # Deep navy – headings, status bar
            "SECONDARY": "#2C3E6B",        # Medium navy – secondary elements
            "ACCENT": "#2563EB",           # Bright medical blue – CTAs, links
            "ACCENT_HOVER": "#1D4ED8",     # Darker accent – button hover
            "ACCENT_LIGHT": "#DBEAFE",     # Very light blue – highlight bg
            # Semantic colours
            "SUCCESS": "#059669",          # Emerald green – completed, active
            "SUCCESS_HOVER": "#047857",    # Darker green – hover
            "SUCCESS_LIGHT": "#D1FAE5",    # Light green – success bg
            "WARNING": "#D97706",          # Amber – warnings, pending
            "WARNING_HOVER": "#B45309",    # Darker amber
            "DANGER": "#DC2626",           # Red – errors, cancellations
            "DANGER_HOVER": "#B91C1C",     # Darker red
            "DANGER_LIGHT": "#FEE2E2",     # Light red – error bg
            # Neutrals
            "LIGHT": "#F1F5F9",            # Very light grey – card bg
            "LIGHTER": "#F8FAFC",          # Almost white – alternate rows
            "WHITE": "#FFFFFF",            # Text on coloured buttons
            "DARK_TEXT": "#0F172A",        # Near black – body text on surfaces
            "LIGHT_TEXT": "#F8FAFC",       # White-ish – text on dark bg
            "MUTED": "#64748B",            # Grey – secondary text
            "BORDER": "#CBD5E1",           # Light border – cards, dividers
            "BORDER_DARK": "#94A3B8",      # Darker border – active inputs
            # Sidebar
            "SIDEBAR_BG": "#0F172A",       # Very dark navy
            "SIDEBAR_ACTIVE": "#1E293B",   # Slightly lighter for active item
            "SIDEBAR_HOVER": "#334155",    # Hover state
            # Background
            "BG": "#F0F4F8",               # Main app background – cool light grey
            "CARD_BG": "#FFFFFF",          # Card background
            # Table
            "TABLE_HEADER_BG": "#1B2A4A",
            "TABLE_HEADER_FG": "#FFFFFF",
            "TABLE_ROW_ALT": "#F8FAFC",
            "TABLE_SELECT": "#DBEAFE",
            "TABLE_SELECT_FG": "#1B2A4A",
            # Surfaces (headers, cards, dialogs, entries) and their text
            "SURFACE": "#FFFFFF",
            "SURFACE_TEXT": "#0F172A",
            "SURFACE_MUTED": "#64748B",
            "HEADING": "#1B2A4A",
        },
        "darkly": {
            "PRIMARY": "#0B1220",          # Very dark navy – status bar, table header
            "SECONDARY": "#1E293B",
            "ACCENT": "#3B82F6",           # Brighter blue for dark backgrounds
            "ACCENT_HOVER": "#2563EB",
            "ACCENT_LIGHT": "#1E3A8A",     # Dark blue – selection / highlight
            "SUCCESS": "#10B981",
            "SUCCESS_HOVER": "#059669",
            "SUCCESS_LIGHT": "#064E3B",
            "WARNING": "#F59E0B",
            "WARNING_HOVER": "#D97706",
            "DANGER": "#EF4444",
            "DANGER_HOVER": "#DC2626",
            "DANGER_LIGHT": "#7F1D1D",
            "LIGHT": "#1E293B",            # Dark raised surface
            "LIGHTER": "#0F172A",
            "WHITE": "#FFFFFF",            # Text on coloured buttons (stays white)
            "DARK_TEXT": "#E2E8F0",        # Light body text on dark surfaces
            "LIGHT_TEXT": "#F8FAFC",
            "MUTED": "#94A3B8",
            "BORDER": "#334155",
            "BORDER_DARK": "#475569",
            "SIDEBAR_BG": "#0B1220",
            "SIDEBAR_ACTIVE": "#1E293B",
            "SIDEBAR_HOVER": "#334155",
            "BG": "#0F172A",               # Main app background – dark navy
            "CARD_BG": "#1E293B",
            "TABLE_HEADER_BG": "#1E293B",
            "TABLE_HEADER_FG": "#F8FAFC",
            "TABLE_ROW_ALT": "#0F172A",
            "TABLE_SELECT": "#1E3A8A",
            "TABLE_SELECT_FG": "#F8FAFC",
            "SURFACE": "#1E293B",          # Headers, cards, dialogs, entries
            "SURFACE_TEXT": "#F8FAFC",
            "SURFACE_MUTED": "#94A3B8",
            "HEADING": "#F1F5F9",
        },
    }

    # Active palette name (defaults to the light theme).
    _active_theme: ClassVar[str] = "flatly"

    # Palette attributes – values are materialised from ``THEMES`` at
    # import time (see the loop after the class body) and swapped by
    # ``apply_theme``.  Declared here so tooling sees them as class attrs.
    PRIMARY: ClassVar[str]
    SECONDARY: ClassVar[str]
    ACCENT: ClassVar[str]
    ACCENT_HOVER: ClassVar[str]
    ACCENT_LIGHT: ClassVar[str]
    SUCCESS: ClassVar[str]
    SUCCESS_HOVER: ClassVar[str]
    SUCCESS_LIGHT: ClassVar[str]
    WARNING: ClassVar[str]
    WARNING_HOVER: ClassVar[str]
    DANGER: ClassVar[str]
    DANGER_HOVER: ClassVar[str]
    DANGER_LIGHT: ClassVar[str]
    LIGHT: ClassVar[str]
    LIGHTER: ClassVar[str]
    WHITE: ClassVar[str]
    DARK_TEXT: ClassVar[str]
    LIGHT_TEXT: ClassVar[str]
    MUTED: ClassVar[str]
    BORDER: ClassVar[str]
    BORDER_DARK: ClassVar[str]
    SIDEBAR_BG: ClassVar[str]
    SIDEBAR_ACTIVE: ClassVar[str]
    SIDEBAR_HOVER: ClassVar[str]
    BG: ClassVar[str]
    CARD_BG: ClassVar[str]
    TABLE_HEADER_BG: ClassVar[str]
    TABLE_HEADER_FG: ClassVar[str]
    TABLE_ROW_ALT: ClassVar[str]
    TABLE_SELECT: ClassVar[str]
    TABLE_SELECT_FG: ClassVar[str]
    SURFACE: ClassVar[str]
    SURFACE_TEXT: ClassVar[str]
    SURFACE_MUTED: ClassVar[str]
    HEADING: ClassVar[str]

    # ── Fonts ──────────────────────────────────────────────────
    FONT_FAMILY = "Segoe UI"
    FONT_FAMILY_MONO = "Consolas"
    FONT_TITLE = (FONT_FAMILY, 18, "bold")
    FONT_HEADING = (FONT_FAMILY, 14, "bold")
    FONT_SUBHEADING = (FONT_FAMILY, 12, "bold")
    FONT_BODY = (FONT_FAMILY, 11)
    FONT_BODY_BOLD = (FONT_FAMILY, 11, "bold")
    FONT_SMALL = (FONT_FAMILY, 10)
    FONT_SMALL_BOLD = (FONT_FAMILY, 10, "bold")
    FONT_BUTTON = (FONT_FAMILY, 11)
    FONT_BUTTON_BOLD = (FONT_FAMILY, 11, "bold")

    # ── Dimensions ─────────────────────────────────────────────
    SIDEBAR_WIDTH = 240
    TOPBAR_HEIGHT = 56
    BUTTON_PADDING = (14, 8)

    @classmethod
    def configure_ttk(cls) -> None:
        """Apply all ttk theme styles globally.

        Call once at application startup (from ``MainWindow``).
        """
        style = ttk.Style()
        style.theme_use("clam")

        # ── General ────────────────────────────────────────────
        style.configure(".", font=cls.FONT_BODY, background=cls.BG)

        # ── Frames ─────────────────────────────────────────────
        style.configure("TFrame", background=cls.BG)
        style.configure("Card.TFrame", background=cls.SURFACE, relief="flat")
        style.configure("Sidebar.TFrame", background=cls.SIDEBAR_BG)
        style.configure("Header.TFrame", background=cls.SURFACE, relief="flat")
        style.configure("StatusBar.TFrame", background=cls.PRIMARY)
        style.configure("Dialog.TFrame", background=cls.SURFACE)

        # ── Labels ─────────────────────────────────────────────
        style.configure("TLabel", background=cls.BG, foreground=cls.DARK_TEXT, font=cls.FONT_BODY)
        style.configure("Title.TLabel", font=cls.FONT_TITLE, foreground=cls.HEADING)
        style.configure("Heading.TLabel", font=cls.FONT_HEADING, foreground=cls.HEADING)
        style.configure("Subheading.TLabel", font=cls.FONT_SUBHEADING, foreground=cls.MUTED)
        style.configure("Card.TLabel", background=cls.SURFACE)
        style.configure("CardTitle.TLabel", background=cls.SURFACE,
                        font=cls.FONT_SUBHEADING, foreground=cls.DARK_TEXT)
        style.configure("CardValue.TLabel", background=cls.SURFACE,
                        font=(cls.FONT_FAMILY, 24, "bold"), foreground=cls.ACCENT)
        style.configure("Sidebar.TLabel", background=cls.SIDEBAR_BG,
                        foreground=cls.LIGHT_TEXT, font=cls.FONT_BODY)
        style.configure("StatusBar.TLabel", background=cls.PRIMARY,
                        foreground=cls.LIGHT_TEXT, font=cls.FONT_SMALL)
        style.configure("Error.TLabel", foreground=cls.DANGER, font=cls.FONT_SMALL)
        style.configure("Success.TLabel", foreground=cls.SUCCESS, font=cls.FONT_SMALL)
        style.configure("Warning.TLabel", foreground=cls.WARNING, font=cls.FONT_SMALL)
        style.configure("Header.TLabel", background=cls.SURFACE,
                        font=cls.FONT_HEADING, foreground=cls.HEADING)
        style.configure("Muted.TLabel", foreground=cls.MUTED, font=cls.FONT_SMALL)

        # ── Labelframe ─────────────────────────────────────────
        style.configure("TLabelframe", background=cls.BG, foreground=cls.DARK_TEXT,
                        font=cls.FONT_BODY_BOLD, relief="solid", bordercolor=cls.BORDER)
        style.configure("TLabelframe.Label", background=cls.BG, foreground=cls.DARK_TEXT,
                        font=cls.FONT_BODY_BOLD)

        # ── Buttons (ttk) ─────────────────────────────────────
        style.configure("TButton", font=cls.FONT_BUTTON, padding=cls.BUTTON_PADDING,
                        foreground=cls.DARK_TEXT)
        style.configure("Primary.TButton", background=cls.ACCENT, foreground=cls.WHITE)
        style.map("Primary.TButton", background=[("active", cls.ACCENT_HOVER)])
        style.configure("Success.TButton", background=cls.SUCCESS, foreground=cls.WHITE)
        style.map("Success.TButton", background=[("active", cls.SUCCESS_HOVER)])
        style.configure("Danger.TButton", background=cls.DANGER, foreground=cls.WHITE)
        style.map("Danger.TButton", background=[("active", cls.DANGER_HOVER)])
        style.configure("Warning.TButton", background=cls.WARNING, foreground=cls.WHITE)
        style.map("Warning.TButton", background=[("active", cls.WARNING_HOVER)])

        # Card buttons (flat, for inside cards)
        style.configure("Card.TButton", background=cls.SURFACE, font=cls.FONT_SMALL)

        # Tool buttons (small, icon-style)
        style.configure("Toolbutton", font=cls.FONT_SMALL, padding=(8, 4))

        # ── Entry ──────────────────────────────────────────────
        style.configure("TEntry", font=cls.FONT_BODY, padding=8,
                        borderwidth=1, relief="solid",
                        fieldbackground=cls.SURFACE, foreground=cls.DARK_TEXT)
        style.map("TEntry",
                  bordercolor=[("focus", cls.ACCENT)],
                  fieldbackground=[("focus", cls.SURFACE)])

        # Search entry specific
        style.configure("Search.TEntry", font=cls.FONT_BODY, padding=8,
                        borderwidth=1, relief="solid",
                        fieldbackground=cls.SURFACE, foreground=cls.DARK_TEXT)

        # ── Combobox ───────────────────────────────────────────
        style.configure("TCombobox", font=cls.FONT_BODY, padding=8,
                        fieldbackground=cls.SURFACE, foreground=cls.DARK_TEXT)
        style.map("TCombobox",
                  bordercolor=[("focus", cls.ACCENT)],
                  fieldbackground=[("focus", cls.SURFACE)])

        # ── Treeview ───────────────────────────────────────────
        style.configure("Treeview",
                        font=cls.FONT_BODY,
                        rowheight=36,
                        background=cls.SURFACE,
                        fieldbackground=cls.SURFACE,
                        foreground=cls.DARK_TEXT,
                        borderwidth=0)
        style.configure("Treeview.Heading",
                        font=cls.FONT_BODY_BOLD,
                        background=cls.TABLE_HEADER_BG,
                        foreground=cls.TABLE_HEADER_FG,
                        relief="flat",
                        padding=(8, 6))
        style.map("Treeview",
                  background=[("selected", cls.TABLE_SELECT)],
                  foreground=[("selected", cls.TABLE_SELECT_FG)])
        style.map("Treeview.Heading",
                  background=[("active", cls.SECONDARY)])

        # ── Notebook (tabs) ────────────────────────────────────
        style.configure("TNotebook", background=cls.BG, borderwidth=0)
        style.configure("TNotebook.Tab", font=cls.FONT_BODY,
                        padding=(20, 10), background=cls.LIGHT)
        style.map("TNotebook.Tab",
                  background=[("selected", cls.WHITE)],
                  foreground=[("selected", cls.ACCENT)])

        # ── Scrollbar ──────────────────────────────────────────
        style.configure("Vertical.TScrollbar",
                        background=cls.BORDER,
                        troughcolor=cls.BG,
                        width=14,
                        arrowsize=14)
        style.configure("Horizontal.TScrollbar",
                        background=cls.BORDER,
                        troughcolor=cls.BG,
                        width=14,
                        arrowsize=14)
        style.map("Vertical.TScrollbar",
                  background=[("active", cls.BORDER_DARK)])
        style.map("Horizontal.TScrollbar",
                  background=[("active", cls.BORDER_DARK)])

        # ── Progressbar ────────────────────────────────────────
        style.configure("TProgressbar",
                        background=cls.ACCENT,
                        troughcolor=cls.LIGHT,
                        thickness=8,
                        borderwidth=0)

        # ── Separator ──────────────────────────────────────────
        style.configure("TSeparator", background=cls.BORDER)

        # ── Sizegrip ───────────────────────────────────────────
        style.configure("TSizegrip", background=cls.BG)

    # ── Theme switching ───────────────────────────────────────

    @classmethod
    def theme_names(cls) -> List[str]:
        """Return the available theme names (e.g. 'flatly', 'darkly').

        Returns:
            List of theme names.
        """
        return list(cls.THEMES.keys())

    @classmethod
    def current_theme(cls) -> str:
        """Return the active theme name.

        Returns:
            The current theme name (e.g. 'flatly').
        """
        return cls._active_theme

    @classmethod
    def apply_theme(cls, name: str) -> None:
        """Switch the whole application to the named palette.

        Swaps every colour class attribute from the palette and
        re-applies the global ttk styles, so existing widgets pick up
        the new colours.  Callers that hold hard-coded ``tk`` widget
        colours (captured at build time) should rebuild their view
        afterwards – see ``MainWindow.refresh_theme``.

        Args:
            name: One of ``Theme.theme_names()`` (e.g. 'flatly').

        Raises:
            ValueError: If the theme name is unknown.
        """
        palette = cls.THEMES.get(name)
        if not palette:
            raise ValueError(
                f"Unknown theme '{name}'. Available: {', '.join(cls.THEMES)}."
            )
        for key, value in palette.items():
            setattr(cls, key, value)
        cls._active_theme = name
        cls.configure_ttk()

    # ── Icon helpers ───────────────────────────────────────────

    # Navigation icons (Unicode / emoji)
    NAV_ICONS = {
        "dashboard": "📊",
        "manage_users": "👥",
        "manage_staff": "👤",
        "manage_doctors": "🩺",
        "manage_departments": "🏢",
        "analytics": "📈",
        "appointments": "📅",
        "reports": "📋",
        "audit_logs": "📜",
        "settings": "⚙️",
        "register_patient": "📝",
        "book_appointment": "➕",
        "search_patient": "🔍",
        "today_appointments": "📋",
        "my_schedule": "🗓️",
        "clinical_records": "🏥",
    }

    @classmethod
    def get_nav_icon(cls, key: str) -> str:
        """Return the Unicode icon for a navigation key.

        Args:
            key: Navigation key string.

        Returns:
            Icon character or a fallback bullet.
        """
        return cls.NAV_ICONS.get(key, "•")

    # ── Color helpers ──────────────────────────────────────────

    @classmethod
    def status_color(cls, status: str) -> str:
        """Return a hex colour appropriate for the given status string.

        Args:
            status: Status string (e.g. 'Active', 'Completed', 'Cancelled').

        Returns:
            Hex colour string.
        """
        s = status.lower().replace(" ", "")
        if s in ("active", "completed", "booked", "approved"):
            return cls.SUCCESS
        elif s in ("inactive", "cancelled", "no_show", "in_progress"):
            return cls.WARNING
        elif s in ("on_leave", "pending"):
            return cls.WARNING
        elif s in ("cancelled", "deleted", "error"):
            return cls.DANGER
        return cls.MUTED


# ── Materialise palette attributes from the active theme ───────
# Runs once at import time so ``Theme.PRIMARY`` etc. exist without
# duplicating the "flatly" values above.  ``apply_theme`` swaps them
# at runtime.
for _key, _value in Theme.THEMES[Theme._active_theme].items():
    setattr(Theme, _key, _value)
