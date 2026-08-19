"""Sidebar navigation widget for role-based dashboards.

Displays icon-labelled navigation buttons with hover/active states.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Tuple, Optional
from src.gui.theme import Theme


class Sidebar(ttk.Frame):
    """Left-hand navigation panel with icon support.

    Buttons use Unicode icons from ``Theme.NAV_ICONS`` for a
    lightweight, cross-platform visual enhancement.
    """

    SEPARATOR_COLOR = Theme.SIDEBAR_ACTIVE

    def __init__(
        self, parent: tk.Widget, on_navigate: Callable[[str], None], **kwargs: Any,
    ) -> None:
        """Initialise the sidebar.

        Args:
            parent: Parent widget.
            on_navigate: Callback invoked with the navigation key when a button is clicked.
            **kwargs: Extra keyword arguments for ttk.Frame.
        """
        super().__init__(parent, style="Sidebar.TFrame", width=Theme.SIDEBAR_WIDTH, **kwargs)
        self.pack_propagate(False)
        self._on_navigate = on_navigate
        self._buttons: List[Tuple[str, tk.Button]] = []
        self._active_key: Optional[str] = None

        # App title / logo area
        title_frame = tk.Frame(self, bg=Theme.SIDEBAR_BG, pady=18)
        title_frame.pack(fill="x")
        tk.Label(
            title_frame, text="🏥 HMS", bg=Theme.SIDEBAR_BG,
            fg=Theme.ACCENT, font=(Theme.FONT_FAMILY, 18, "bold"),
        ).pack()
        tk.Label(
            title_frame, text="Hospital Management", bg=Theme.SIDEBAR_BG,
            fg=Theme.MUTED, font=Theme.FONT_SMALL,
        ).pack()

        # Separator
        sep = tk.Frame(self, bg=self.SEPARATOR_COLOR, height=1)
        sep.pack(fill="x", padx=16, pady=(0, 8))

        # Navigation container
        self._nav_frame = tk.Frame(self, bg=Theme.SIDEBAR_BG)
        self._nav_frame.pack(fill="both", expand=True, pady=4)

    def set_items(self, items: List[Tuple[str, str]]) -> None:
        """Populate the sidebar with icon-labelled navigation buttons.

        Args:
            items: List of (key, label) tuples.  The key is used to look up
                   an icon from ``Theme.NAV_ICONS`` and is passed to the
                   ``on_navigate`` callback when the button is clicked.
        """
        for btn in self._buttons:
            btn[1].destroy()
        self._buttons.clear()

        for key, label in items:
            icon = Theme.get_nav_icon(key)
            btn_text = f"  {icon}  {label}"

            btn = tk.Button(
                self._nav_frame,
                text=btn_text,
                bg=Theme.SIDEBAR_BG,
                fg=Theme.LIGHT_TEXT,
                font=Theme.FONT_BODY,
                anchor="w",
                padx=20,
                pady=10,
                bd=0,
                activebackground=Theme.SIDEBAR_HOVER,
                activeforeground=Theme.LIGHT_TEXT,
                cursor="hand2",
                compound="left",
                command=lambda k=key: self._on_click(k),
            )
            btn.pack(fill="x")
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=Theme.SIDEBAR_HOVER))
            btn.bind("<Leave>", lambda e, b=btn, k=key: b.configure(
                bg=Theme.SIDEBAR_ACTIVE if k == self._active_key else Theme.SIDEBAR_BG
            ))
            self._buttons.append((key, btn))

    def _on_click(self, key: str) -> None:
        """Handle a navigation button click.

        Args:
            key: The navigation key associated with the clicked button.
        """
        self.set_active(key)
        self._on_navigate(key)

    def set_active(self, key: str) -> None:
        """Visually highlight the active navigation button.

        Args:
            key: The navigation key to mark as active.
        """
        self._active_key = key
        for k, btn in self._buttons:
            if k == key:
                btn.configure(
                    bg=Theme.SIDEBAR_ACTIVE, fg=Theme.ACCENT,
                    font=Theme.FONT_BODY_BOLD,
                )
            else:
                btn.configure(
                    bg=Theme.SIDEBAR_BG, fg=Theme.LIGHT_TEXT,
                    font=Theme.FONT_BODY,
                )