"""Receptionist dashboard GUI."""
import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable, Dict, Any
from src.gui.theme import Theme
from src.gui.common.base_view import BaseView, create_card


class ReceptionistDashboard(BaseView):
    """Landing page for receptionists with quick patient and appointment links."""

    def __init__(
        self,
        parent: tk.Widget,
        stats: Dict[str, Any],
        on_navigate: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> None:
        """Initialise the receptionist dashboard.

        Args:
            parent: Parent tkinter widget.
            stats: Summary statistics.
            on_navigate: Callback for navigation.
        """
        super().__init__(parent, **kwargs)
        self._stats = stats
        self._on_navigate = on_navigate
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the dashboard layout."""
        header = ttk.Frame(self, style="Header.TFrame", padding=16)
        header.pack(fill="x")
        ttk.Label(header, text="Receptionist Dashboard", style="Heading.TLabel").pack(anchor="w")

        content = ttk.Frame(self, style="TFrame", padding=16)
        content.pack(fill="both", expand=True)
        content.columnconfigure((0, 1, 2), weight=1, uniform="card")

        # Summary cards
        cards = ttk.Frame(content, style="TFrame")
        cards.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 16))
        cards.columnconfigure((0, 1, 2), weight=1, uniform="card")
        create_card(cards, "Total Patients", str(self._stats.get("total_patients", 0)), 0, 0)
        create_card(cards, "Today's Appointments", str(self._stats.get("today_appointments", 0)), 0, 1)
        create_card(cards, "Active Doctors", str(self._stats.get("total_doctors", 0)), 0, 2)

        # Quick actions
        actions_frame = ttk.LabelFrame(content, text="Quick Actions", padding=16)
        actions_frame.grid(row=1, column=0, columnspan=3, sticky="ew")
        actions_frame.columnconfigure((0, 1, 2), weight=1)

        actions = [
            ("register_patient", "Register Patient", Theme.SUCCESS),
            ("book_appointment", "Book Appointment", Theme.ACCENT),
            ("search_patient", "Search Patient", Theme.WARNING),
        ]
        for idx, (key, label, color) in enumerate(actions):
            btn = tk.Button(
                actions_frame, text=label, bg=color, fg=Theme.WHITE,
                font=Theme.FONT_BUTTON_BOLD, activebackground=Theme.PRIMARY,
                activeforeground=Theme.WHITE, cursor="hand2", bd=0,
                padx=16, pady=12,
                command=lambda k=key: self._on_navigate and self._on_navigate(k),
            )
            btn.grid(row=0, column=idx, padx=8, pady=4, sticky="ew")
