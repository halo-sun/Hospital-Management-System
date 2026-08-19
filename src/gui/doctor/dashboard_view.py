"""Doctor dashboard GUI – today's appointments and quick actions."""
import tkinter as tk
from tkinter import ttk
from datetime import date
from typing import Optional, Callable, Dict, Any, List
from src.gui.theme import Theme
from src.gui.common.base_view import BaseView, create_card


class DoctorDashboard(BaseView):
    """Landing page for doctors showing today's schedule and clinical actions."""

    def __init__(
        self,
        parent: tk.Widget,
        doctor_name: str,
        today_appointments: List[Dict[str, Any]],
        on_navigate: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> None:
        """Initialise the doctor dashboard.

        Args:
            parent: Parent tkinter widget.
            doctor_name: Display name of the doctor.
            today_appointments: List of today's appointment records.
            on_navigate: Callback for navigation.
        """
        super().__init__(parent, **kwargs)
        self._doctor_name = doctor_name
        self._appointments = today_appointments
        self._on_navigate = on_navigate
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the dashboard layout."""
        header = ttk.Frame(self, style="Header.TFrame", padding=16)
        header.pack(fill="x")
        ttk.Label(header, text=f"Welcome, Dr. {self._doctor_name}", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(header, text=date.today().strftime("%A, %B %d, %Y"), style="Subheading.TLabel").pack(anchor="w", pady=(4, 0))

        content = ttk.Frame(self, style="TFrame", padding=16)
        content.pack(fill="both", expand=True)
        content.columnconfigure((0, 1), weight=1, uniform="card")

        # Summary cards
        cards = ttk.Frame(content, style="TFrame")
        cards.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        cards.columnconfigure((0, 1), weight=1, uniform="card")
        create_card(cards, "Today's Appointments", str(len(self._appointments)), 0, 0)

        completed = sum(1 for a in self._appointments if a.get("status") == "Completed")
        create_card(cards, "Completed", str(completed), 0, 1)

        # Today's appointments table
        table_frame = ttk.LabelFrame(content, text="Today's Appointments", padding=8)
        table_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=8)
        content.rowconfigure(1, weight=1)

        columns = ("time", "patient", "status", "notes")
        tree = self.create_treeview(
            table_frame, columns=columns,
            headings=("Time", "Patient", "Status", "Notes"),
            height=12,
        )
        tree.column("time", width=120, anchor="center")
        tree.column("patient", width=200)
        tree.column("status", width=100, anchor="center")
        tree.column("notes", width=200)

        for appt in self._appointments:
            start = appt.get("start_time", "")
            end = appt.get("end_time", "")
            if hasattr(start, "strftime"):
                start = start.strftime("%H:%M")
            if hasattr(end, "strftime"):
                end = end.strftime("%H:%M")
            tree.insert("", "end", values=(
                f"{start} - {end}",
                appt.get("patient_name", appt.get("patient_id", "")),
                appt.get("status", ""),
                appt.get("notes", "")[:50],
            ))

        # Quick actions
        actions_frame = ttk.LabelFrame(content, text="Quick Actions", padding=16)
        actions_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=8)
        actions_frame.columnconfigure((0, 1), weight=1)

        actions = [
            ("my_schedule", "My Schedule", Theme.ACCENT),
            ("clinical_records", "Clinical Records", Theme.SUCCESS),
        ]
        for idx, (key, label, color) in enumerate(actions):
            btn = tk.Button(
                actions_frame, text=label, bg=color, fg=Theme.WHITE,
                font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0,
                padx=16, pady=10,
                command=lambda k=key: self._on_navigate and self._on_navigate(k),
            )
            btn.grid(row=0, column=idx, padx=8, pady=4, sticky="ew")
