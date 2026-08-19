"""Admin dashboard GUI – summary cards and navigation to admin modules."""
import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable, Dict, Any, List
from src.gui.theme import Theme
from src.gui.common.base_view import BaseView, create_card


class AdminDashboard(BaseView):
    """Main landing page for administrators.

    Shows summary statistics and links to user, doctor, department,
    and report management screens.
    """

    def __init__(
        self,
        parent: tk.Widget,
        stats: Dict[str, Any],
        on_navigate: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> None:
        """Initialise the admin dashboard.

        Args:
            parent: Parent tkinter widget.
            stats: Dictionary with total_patients, total_doctors, etc.
            on_navigate: Optional callback for module navigation.
        """
        super().__init__(parent, **kwargs)
        self._stats = stats
        self._on_navigate = on_navigate
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the dashboard layout."""
        # Header
        header = ttk.Frame(self, style="Header.TFrame", padding=16)
        header.pack(fill="x")
        ttk.Label(header, text="Admin Dashboard", style="Heading.TLabel").pack(anchor="w")

        # Content area with scrollbar
        canvas = tk.Canvas(self, bg=Theme.BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self._scroll_frame = ttk.Frame(canvas, style="TFrame")

        self._scroll_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self._scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        content = self._scroll_frame
        content.columnconfigure((0, 1, 2, 3), weight=1, uniform="card")

        # ── Summary Cards ─────────────────────────────────────
        cards_frame = ttk.Frame(content, style="TFrame", padding=16)
        cards_frame.grid(row=0, column=0, columnspan=4, sticky="ew", padx=16, pady=(16, 8))
        cards_frame.columnconfigure((0, 1, 2, 3), weight=1, uniform="card")

        create_card(cards_frame, "Total Patients", str(self._stats.get("total_patients", 0)), 0, 0)
        create_card(cards_frame, "Total Doctors", str(self._stats.get("total_doctors", 0)), 0, 1)
        create_card(cards_frame, "Departments", str(self._stats.get("total_departments", 0)), 0, 2)
        create_card(cards_frame, "Today's Appointments", str(self._stats.get("today_appointments", 0)), 0, 3)

        # ── Quick Actions ─────────────────────────────────────
        actions_frame = ttk.LabelFrame(content, text="Quick Actions", padding=16)
        actions_frame.grid(row=1, column=0, columnspan=4, sticky="ew", padx=16, pady=8)
        actions_frame.columnconfigure((0, 1, 2, 3), weight=1)

        actions = [
            ("manage_users", "👥 Manage Users"),
            ("manage_doctors", "🩺 Manage Doctors"),
            ("manage_departments", "🏢 Departments"),
            ("reports", "📊 Reports"),
        ]
        for idx, (key, label) in enumerate(actions):
            btn = tk.Button(
                actions_frame, text=label, bg=Theme.ACCENT, fg=Theme.WHITE,
                font=Theme.FONT_BUTTON_BOLD, activebackground=Theme.PRIMARY,
                activeforeground=Theme.WHITE, cursor="hand2", bd=0,
                padx=16, pady=12,
                command=lambda k=key: self._on_navigate and self._on_navigate(k),
            )
            btn.grid(row=0, column=idx, padx=8, pady=4, sticky="ew")
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=Theme.PRIMARY))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=Theme.ACCENT))

    def update_stats(self, stats: Dict[str, Any]) -> None:
        """Refresh the summary card values.

        Args:
            stats: Updated statistics dictionary.
        """
        self._stats = stats
        self._build_ui()
