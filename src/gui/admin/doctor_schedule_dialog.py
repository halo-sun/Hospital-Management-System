"""Doctor schedule dialog – reusable modal for managing weekly availability.

Allows administrators to view and edit a doctor's weekly working hours
per day of the week, including availability toggling.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import time
from typing import Optional, Callable, Dict, Any, List, Tuple
from src.gui.theme import Theme
from src.utils.validators import validate_schedule_data
from src.utils.formatters import format_date, parse_date_for_input, DISPLAY_DATE_FORMAT


# ── Day names ──────────────────────────────────────────────────
_DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


class DoctorScheduleDialog(tk.Toplevel):
    """Modal dialog for editing a doctor's weekly schedule."""

    def __init__(
        self,
        parent: tk.Widget,
        doctor_name: str,
        schedule: List[Dict[str, Any]],
        on_save: Callable[[int, int, time, time, bool], Tuple[bool, str]],
        **kwargs,
    ) -> None:
        """Initialise the schedule editor dialog.

        Args:
            parent: Parent window.
            doctor_name: Display name for the doctor.
            schedule: List of existing schedule records.
            on_save: Callback(doctor_id, day_of_week, start, end, is_available)
                     that returns (success, message).
        """
        super().__init__(parent)
        self.title(f"Schedule - Dr. {doctor_name}")
        self.geometry("620x520")
        self.configure(bg=Theme.BG)
        self.transient(parent)
        self.grab_set()

        self._schedule = schedule or []
        self._on_save = on_save
        # Build a lookup by day_of_week
        self._schedule_by_day: Dict[int, Dict[str, Any]] = {
            s["day_of_week"]: s for s in schedule if s.get("is_available")
        }
        self._vars: Dict[int, Dict[str, tk.Variable]] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the schedule editor layout."""
        # Header
        header = ttk.Frame(self, style="Header.TFrame", padding=16)
        header.pack(fill="x")
        ttk.Label(header, text="Weekly Schedule", style="Heading.TLabel").pack(anchor="w")

        # Instructions
        info = ttk.Frame(self, style="TFrame", padding=(16, 8))
        info.pack(fill="x")
        ttk.Label(
            info,
            text="Set working hours for each day of the week. "
                 "Uncheck a day to mark it as non-working.",
            font=Theme.FONT_SMALL, foreground=Theme.MUTED,
        ).pack(anchor="w")

        # Scrollable schedule grid
        canvas = tk.Canvas(self, bg=Theme.BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        grid_frame = ttk.Frame(canvas, style="TFrame", padding=16)
        grid_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=grid_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Column headers
        ttk.Label(grid_frame, text="Day", font=Theme.FONT_BODY_BOLD).grid(
            row=0, column=0, sticky="w", padx=(0, 16), pady=4
        )
        ttk.Label(grid_frame, text="Available", font=Theme.FONT_BODY_BOLD).grid(
            row=0, column=1, sticky="w", padx=(0, 16), pady=4
        )
        ttk.Label(grid_frame, text="Start Time", font=Theme.FONT_BODY_BOLD).grid(
            row=0, column=2, sticky="w", padx=(0, 16), pady=4
        )
        ttk.Label(grid_frame, text="End Time", font=Theme.FONT_BODY_BOLD).grid(
            row=0, column=3, sticky="w", padx=(0, 16), pady=4
        )

        # Time options (hour:min AM/PM)
        time_options = self._generate_time_options()

        for day_idx in range(7):
            row = day_idx + 1
            existing = self._schedule_by_day.get(day_idx, {})
            is_available = existing.get("is_available", True)
            start = existing.get("start_time")
            end = existing.get("end_time")

            start_str = self._time_to_str(start) if start else "09:00"
            end_str = self._time_to_str(end) if end else "17:00"

            # Day name
            ttk.Label(grid_frame, text=_DAY_NAMES[day_idx], font=Theme.FONT_BODY).grid(
                row=row, column=0, sticky="w", padx=(0, 16), pady=6
            )

            # Available checkbox
            avail_var = tk.BooleanVar(value=is_available)
            cb = tk.Checkbutton(
                grid_frame, variable=avail_var, bg=Theme.BG,
                activebackground=Theme.BG,
            )
            cb.grid(row=row, column=1, padx=(0, 16), pady=6)

            # Start time
            start_var = tk.StringVar(value=start_str)
            start_combo = ttk.Combobox(
                grid_frame, textvariable=start_var, values=time_options,
                width=10, state="readonly", font=Theme.FONT_BODY,
            )
            start_combo.grid(row=row, column=2, padx=(0, 8), pady=6)
            start_combo.bind("<<ComboboxSelected>>", lambda e, v=start_var: v.set(e.widget.get()))

            # End time
            end_var = tk.StringVar(value=end_str)
            end_combo = ttk.Combobox(
                grid_frame, textvariable=end_var, values=time_options,
                width=10, state="readonly", font=Theme.FONT_BODY,
            )
            end_combo.grid(row=row, column=3, padx=(0, 8), pady=6)

            self._vars[day_idx] = {
                "available": avail_var,
                "start": start_var,
                "end": end_var,
            }

        # Save / Cancel buttons
        btn_frame = ttk.Frame(self, style="TFrame", padding=(16, 8, 16, 16))
        btn_frame.pack(fill="x")

        tk.Button(
            btn_frame, text="Save Schedule", bg=Theme.SUCCESS, fg=Theme.WHITE,
            font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=16, pady=8,
            command=self._handle_save_all,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_frame, text="Cancel", bg=Theme.DANGER, fg=Theme.WHITE,
            font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=16, pady=8,
            command=self.destroy,
        ).pack(side="left")

    # ── Helpers ────────────────────────────────────────────────

    @staticmethod
    def _generate_time_options() -> List[str]:
        """Generate 30-minute interval time strings.

        Returns:
            List of time strings like "09:00", "09:30", ..., "17:30".
        """
        options = []
        for hour in range(6, 22):  # 6 AM to 9 PM
            for minute in (0, 30):
                options.append(f"{hour:02d}:{minute:02d}")
        return options

    @staticmethod
    def _time_to_str(t) -> str:
        """Convert a time value to ``HH:MM`` string.

        Args:
            t: A time, datetime, string, or None.

        Returns:
            ``HH:MM`` formatted string.
        """
        if t is None:
            return "09:00"
        if isinstance(t, time):
            return f"{t.hour:02d}:{t.minute:02d}"
        if hasattr(t, "hour"):
            return f"{t.hour:02d}:{t.minute:02d}"
        s = str(t)
        if len(s) >= 5:
            return s[:5]
        return "09:00"

    @staticmethod
    def _parse_time(time_str: str) -> Optional[time]:
        """Parse an ``HH:MM`` string into a time object.

        Args:
            time_str: String like "09:30".

        Returns:
            A ``datetime.time`` object or None.
        """
        try:
            parts = time_str.split(":")
            return time(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            return None

    def _handle_save_all(self) -> None:
        """Save all schedule entries that have changed."""
        errors: List[str] = []
        saves: List[Tuple[int, time, time, bool]] = []

        for day_idx in range(7):
            v = self._vars.get(day_idx)
            if not v:
                continue

            is_available = v["available"].get()
            start_str = v["start"].get()
            end_str = v["end"].get()

            if not is_available:
                # Save as unavailable only if it was previously available
                existing = self._schedule_by_day.get(day_idx, {})
                if existing.get("is_available", True) is not False:
                    start = time(0, 0)
                    end = time(0, 0)
                    saves.append((day_idx, start, end, False))
                continue

            start = self._parse_time(start_str)
            end = self._parse_time(end_str)

            if not start or not end:
                errors.append(f"{_DAY_NAMES[day_idx]}: invalid time.")
                continue

            valid, msg = validate_schedule_data(day_idx, start, end)
            if not valid:
                errors.append(f"{_DAY_NAMES[day_idx]}: {msg}")
                continue

            # Check if this entry actually changed
            existing = self._schedule_by_day.get(day_idx, {})
            old_start = existing.get("start_time")
            old_end = existing.get("end_time")
            old_avail = existing.get("is_available", True)

            if (old_start != start or old_end != end or old_avail != is_available):
                saves.append((day_idx, start, end, is_available))

        if errors:
            messagebox.showerror("Validation Errors", "\n".join(errors), parent=self)
            return

        # Persist all changed entries
        for day_idx, start, end, available in saves:
            success, msg = self._on_save(day_idx, start, end, available)
            if not success:
                errors.append(f"{_DAY_NAMES[day_idx]}: {msg}")

        if errors:
            messagebox.showerror("Save Errors", "\n".join(errors), parent=self)
            return

        messagebox.showinfo("Success", "Schedule updated successfully.", parent=self)
        self.destroy()


class DoctorLeaveDialog(tk.Toplevel):
    """Modal dialog for adding a leave record for a doctor."""

    def __init__(
        self,
        parent: tk.Widget,
        doctor_name: str,
        on_submit: Callable,
        **kwargs,
    ) -> None:
        """Initialise the leave dialog.

        Args:
            parent: Parent window.
            doctor_name: Display name for the doctor.
            on_submit: Callback invoked with leave data dict.
        """
        super().__init__(parent)
        self.title(f"Add Leave - Dr. {doctor_name}")
        self.geometry("400x300")
        self.configure(bg=Theme.BG)
        self.transient(parent)
        self.grab_set()
        self._on_submit = on_submit
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the leave form layout."""
        form = ttk.Frame(self, padding=24, style="TFrame")
        form.pack(fill="both", expand=True)

        ttk.Label(form, text="Add Leave Record", style="Heading.TLabel").pack(
            anchor="w", pady=(0, 16)
        )

        # Start date
        ttk.Label(form, text=f"Start Date ({DISPLAY_DATE_FORMAT}) *", font=Theme.FONT_BODY).pack(anchor="w")
        self._start_var = tk.StringVar()
        ttk.Entry(form, textvariable=self._start_var, width=30, font=Theme.FONT_BODY).pack(
            fill="x", pady=(2, 12)
        )

        # End date
        ttk.Label(form, text=f"End Date ({DISPLAY_DATE_FORMAT}) *", font=Theme.FONT_BODY).pack(anchor="w")
        self._end_var = tk.StringVar()
        ttk.Entry(form, textvariable=self._end_var, width=30, font=Theme.FONT_BODY).pack(
            fill="x", pady=(2, 12)
        )

        # Reason
        ttk.Label(form, text="Reason", font=Theme.FONT_BODY).pack(anchor="w")
        self._reason_var = tk.StringVar()
        ttk.Entry(form, textvariable=self._reason_var, width=30, font=Theme.FONT_BODY).pack(
            fill="x", pady=(2, 16)
        )

        # Buttons
        btn_frame = ttk.Frame(form, style="TFrame")
        btn_frame.pack(fill="x")

        tk.Button(
            btn_frame, text="Add Leave", bg=Theme.WARNING, fg=Theme.WHITE,
            font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=16, pady=6,
            command=self._handle_submit,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_frame, text="Cancel", bg=Theme.DANGER, fg=Theme.WHITE,
            font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=16, pady=6,
            command=self.destroy,
        ).pack(side="left")

    def _handle_submit(self) -> None:
        """Collect data and invoke the submit callback."""
        start = self._start_var.get().strip()
        end = self._end_var.get().strip()

        if not start or not end:
            messagebox.showwarning("Warning", "Start and end dates are required.", parent=self)
            return

        data = {
            "leave_start_date": start,
            "leave_end_date": end,
            "reason": self._reason_var.get().strip(),
            "status": "Approved",
        }
        self._on_submit(data)
        self.destroy()
