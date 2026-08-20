"""Appointment booking and management views."""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, time, datetime, timedelta
from typing import Optional, Callable, Dict, Any, List
from src.gui.theme import Theme
from src.gui.common.base_view import BaseView


class AppointmentBookingView(BaseView):
    """Multi-step form for booking a new appointment."""

    def __init__(
        self,
        parent: tk.Widget,
        departments: List[Dict[str, Any]],
        patients: List[Dict[str, Any]],
        on_book: Callable,
        on_cancel: Optional[Callable] = None,
        **kwargs,
    ) -> None:
        """Initialise the booking view.

        Args:
            parent: Parent tkinter widget.
            departments: List of department dicts.
            patients: List of patient dicts.
            on_book: Callback invoked with booking data dict.
            on_cancel: Optional callback for the cancel button.
        """
        super().__init__(parent, **kwargs)
        self._departments = departments
        self._patients = patients
        self._on_book = on_book
        self._on_cancel = on_cancel
        self._doctors: List[Dict[str, Any]] = []
        self._slots: List[Dict[str, Any]] = []
        self._selected_doctor_id: Optional[int] = None
        self._selected_date: Optional[date] = None
        self._selected_slot: Optional[Dict[str, Any]] = None
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the booking form."""
        header = ttk.Frame(self, style="Header.TFrame", padding=16)
        header.pack(fill="x")
        ttk.Label(header, text="Book Appointment", style="Heading.TLabel").pack(anchor="w")

        form = ttk.Frame(self, style="TFrame", padding=24)
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)

        row = 0

        # Patient
        patient_ids = [f"{p.get('patient_id', '')} - {p.get('full_name', '')}" for p in self._patients]
        ttk.Label(form, text="Patient *", font=Theme.FONT_BODY).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=6)
        self._patient_combo = ttk.Combobox(form, values=patient_ids, width=50, state="readonly", font=Theme.FONT_BODY)
        self._patient_combo.grid(row=row, column=1, sticky="ew", pady=6)
        row += 1

        # Department
        dept_names = [d.get("department_name", "") for d in self._departments]
        ttk.Label(form, text="Department", font=Theme.FONT_BODY).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=6)
        self._dept_combo = ttk.Combobox(form, values=dept_names, width=50, state="readonly", font=Theme.FONT_BODY)
        self._dept_combo.grid(row=row, column=1, sticky="ew", pady=6)
        self._dept_combo.bind("<<ComboboxSelected>>", self._on_department_selected)
        row += 1

        # Doctor
        ttk.Label(form, text="Doctor *", font=Theme.FONT_BODY).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=6)
        self._doctor_combo = ttk.Combobox(form, values=[], width=50, state="readonly", font=Theme.FONT_BODY)
        self._doctor_combo.grid(row=row, column=1, sticky="ew", pady=6)
        self._doctor_combo.bind("<<ComboboxSelected>>", self._on_doctor_selected)
        row += 1

        # Date
        ttk.Label(form, text="Date (YYYY-MM-DD) *", font=Theme.FONT_BODY).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=6)
        self._date_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        date_entry = ttk.Entry(form, textvariable=self._date_var, width=50, font=Theme.FONT_BODY)
        date_entry.grid(row=row, column=1, sticky="ew", pady=6)
        row += 1

        # Notes
        ttk.Label(form, text="Notes", font=Theme.FONT_BODY).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=6)
        self._notes_var = tk.StringVar()
        ttk.Entry(form, textvariable=self._notes_var, width=50, font=Theme.FONT_BODY).grid(row=row, column=1, sticky="ew", pady=6)
        row += 1

        # Load slots button
        tk.Button(
            form, text="Load Available Slots", bg=Theme.ACCENT, fg=Theme.WHITE,
            font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=16, pady=6,
            command=self._load_slots,
        ).grid(row=row, column=0, columnspan=2, pady=8)
        row += 1

        # Slots table
        slots_frame = ttk.LabelFrame(form, text="Available Time Slots", padding=8)
        slots_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=8)

        columns = ("time", "status")
        self._slots_tree = ttk.Treeview(slots_frame, columns=columns, show="headings", height=6)
        self._slots_tree.heading("time", text="Time Slot")
        self._slots_tree.heading("status", text="Status")
        self._slots_tree.column("time", width=200, anchor="center")
        self._slots_tree.column("status", width=120, anchor="center")
        self._slots_tree.pack(fill="x")
        self._slots_tree.bind("<<TreeviewSelect>>", self._on_slot_select)
        row += 1

        # Buttons
        btn_frame = ttk.Frame(form, style="TFrame")
        btn_frame.grid(row=row, column=0, columnspan=2, pady=(12, 0))

        self._book_btn = tk.Button(
            btn_frame, text="Book Appointment", bg=Theme.SUCCESS, fg=Theme.WHITE,
            font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=20, pady=8,
            command=self._handle_book, state="disabled",
        )
        self._book_btn.pack(side="left", padx=(0, 8))

        if self._on_cancel:
            tk.Button(
                btn_frame, text="Cancel", bg=Theme.DANGER, fg=Theme.WHITE,
                font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=20, pady=8,
                command=self._on_cancel,
            ).pack(side="left")

    def set_doctors(self, doctors: List[Dict[str, Any]]) -> None:
        """Populate the doctor dropdown.

        Args:
            doctors: List of doctor dictionaries.
        """
        self._doctors = doctors
        names = [f"Dr. {d.get('full_name', '')} ({d.get('specialization', '')})" for d in doctors]
        self._doctor_combo["values"] = names

    def set_slots(self, slots: List[Dict[str, Any]]) -> None:
        """Populate the time-slots table.

        Args:
            slots: List of slot dicts with 'start_time', 'end_time', 'available'.
        """
        self._slots = slots
        self._slots_tree.delete(*self._slots_tree.get_children())
        for s in slots:
            start = s["start_time"]
            end = s["end_time"]
            if hasattr(start, "strftime"):
                start = start.strftime("%H:%M")
            if hasattr(end, "strftime"):
                end = end.strftime("%H:%M")
            status = "Available" if s["available"] else "Booked"
            tag = "available" if s["available"] else "booked"
            self._slots_tree.insert("", "end", values=(f"{start} - {end}", status), tags=(tag,))
        self._slots_tree.tag_configure("available", foreground=Theme.SUCCESS)
        self._slots_tree.tag_configure("booked", foreground=Theme.DANGER)

    def on_departments_loaded(self, departments: List[Dict[str, Any]]) -> None:
        """Update the departments list.

        Args:
            departments: List of department dicts.
        """
        self._departments = departments
        names = [d.get("department_name", "") for d in departments]
        self._dept_combo["values"] = names

    def on_doctors_loaded(self, doctors: List[Dict[str, Any]]) -> None:
        """Update the doctors list after department selection.

        Args:
            doctors: List of doctor dicts.
        """
        self.set_doctors(doctors)

    def on_slots_loaded(self, slots: List[Dict[str, Any]]) -> None:
        """Update the slots list after date/doctor selection.

        Args:
            slots: List of slot dicts.
        """
        self.set_slots(slots)

    def show_error(self, message: str) -> None:
        """Show an error message.

        Args:
            message: The error text.
        """
        messagebox.showerror("Error", message, parent=self)

    def show_success(self, message: str) -> None:
        """Show a success message.

        Args:
            message: The success text.
        """
        messagebox.showinfo("Success", message, parent=self)

    # ── Internal callbacks ─────────────────────────────────────

    def _on_department_selected(self, event=None) -> None:
        """Handle department dropdown selection."""
        idx = self._dept_combo.current()
        if idx >= 0 and idx < len(self._departments):
            dept = self._departments[idx]
            self._on_book(("department_selected", dept.get("department_id")))

    def _on_doctor_selected(self, event=None) -> None:
        """Handle doctor dropdown selection."""
        idx = self._doctor_combo.current()
        if idx >= 0 and idx < len(self._doctors):
            self._selected_doctor_id = self._doctors[idx].get("doctor_id")

    def _on_slot_select(self, event=None) -> None:
        """Handle slot selection."""
        selection = self._slots_tree.selection()
        if selection:
            idx = self._slots_tree.index(selection[0])
            if idx < len(self._slots):
                self._selected_slot = self._slots[idx]
                self._book_btn.configure(state="normal")

    def _load_slots(self) -> None:
        """Load available slots for the selected doctor and date."""
        if not self._selected_doctor_id:
            messagebox.showwarning("Warning", "Please select a doctor first.", parent=self)
            return
        try:
            self._selected_date = datetime.strptime(self._date_var.get(), "%Y-%m-%d").date()
        except ValueError:
            messagebox.showwarning("Warning", "Please enter a valid date (YYYY-MM-DD).", parent=self)
            return
        self._on_book(("load_slots", self._selected_doctor_id, self._selected_date))

    def _handle_book(self) -> None:
        """Validate and submit the booking."""
        patient_idx = self._patient_combo.current()
        if patient_idx < 0:
            messagebox.showwarning("Warning", "Please select a patient.", parent=self)
            return
        if not self._selected_slot:
            messagebox.showwarning("Warning", "Please select a time slot.", parent=self)
            return
        if not self._selected_slot.get("available"):
            messagebox.showwarning("Warning", "Selected slot is not available.", parent=self)
            return

        patient = self._patients[patient_idx]
        data = {
            "patient_id": patient.get("patient_id"),
            "doctor_id": self._selected_doctor_id,
            "appointment_date": self._selected_date,
            "start_time": self._selected_slot["start_time"],
            "end_time": self._selected_slot["end_time"],
            "notes": self._notes_var.get().strip(),
        }
        self._on_book(("book", data))


class AppointmentListView(BaseView):
    """Table view for listing and managing appointments."""

    def __init__(
        self,
        parent: tk.Widget,
        appointments: List[Dict[str, Any]],
        on_cancel: Optional[Callable[[int], None]] = None,
        on_refresh: Optional[Callable] = None,
        **kwargs,
    ) -> None:
        """Initialise the appointment list.

        Args:
            parent: Parent tkinter widget.
            appointments: List of appointment dicts.
            on_cancel: Callback when cancel is clicked.
            on_refresh: Callback to refresh the list.
        """
        super().__init__(parent, **kwargs)
        self._appointments = appointments
        self._on_cancel = on_cancel
        self._on_refresh = on_refresh
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the list view."""
        header = ttk.Frame(self, style="Header.TFrame", padding=16)
        header.pack(fill="x")
        ttk.Label(header, text="Appointments", style="Heading.TLabel").pack(side="left")

        if self._on_refresh:
            tk.Button(
                header, text="Refresh", bg=Theme.ACCENT, fg=Theme.WHITE,
                font=Theme.FONT_SMALL, cursor="hand2", bd=0, padx=12, pady=4,
                command=self._on_refresh,
            ).pack(side="right")

        table_frame = ttk.Frame(self, style="TFrame", padding=16)
        table_frame.pack(fill="both", expand=True)

        columns = ("id", "patient", "doctor", "date", "time", "status")
        self._tree = self.create_treeview(
            table_frame, columns=columns,
            headings=("ID", "Patient", "Doctor", "Date", "Time", "Status"),
            height=15,
        )
        self._tree.column("id", width=60, anchor="center")
        self._tree.column("patient", width=180)
        self._tree.column("doctor", width=180)
        self._tree.column("date", width=100, anchor="center")
        self._tree.column("time", width=120, anchor="center")
        self._tree.column("status", width=100, anchor="center")

        self.populate(self._appointments)

        # Action buttons
        btn_frame = ttk.Frame(self, style="TFrame", padding=(16, 0))
        btn_frame.pack(fill="x")

        if self._on_cancel:
            tk.Button(
                btn_frame, text="Cancel Selected", bg=Theme.DANGER, fg=Theme.WHITE,
                font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=12, pady=6,
                command=self._handle_cancel,
            ).pack(side="left")

    def populate(self, appointments: List[Dict[str, Any]]) -> None:
        """Fill the tree with appointment records.

        Args:
            appointments: List of appointment dictionaries.
        """
        self._tree.delete(*self._tree.get_children())
        for a in appointments:
            appt_date = a.get("appointment_date", "")
            if hasattr(appt_date, "strftime"):
                appt_date = appt_date.strftime("%Y-%m-%d")
            start = a.get("start_time", "")
            end = a.get("end_time", "")
            if hasattr(start, "strftime"):
                start = start.strftime("%H:%M")
            if hasattr(end, "strftime"):
                end = end.strftime("%H:%M")

            self._tree.insert("", "end", values=(
                a.get("appointment_id", ""),
                a.get("patient_name", a.get("patient_id", "")),
                a.get("doctor_name", f"Dr. {a.get('doctor_id', '')}"),
                appt_date,
                f"{start} - {end}",
                a.get("status", ""),
            ), tags=(a.get("status", "").lower(),))

        self._tree.tag_configure("booked", foreground=Theme.ACCENT)
        self._tree.tag_configure("completed", foreground=Theme.SUCCESS)
        self._tree.tag_configure("cancelled", foreground=Theme.DANGER)
        self.apply_default_sort(self._tree)

    def _handle_cancel(self) -> None:
        """Cancel the selected appointment."""
        selection = self._tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an appointment to cancel.", parent=self)
            return
        appt_id = self._tree.item(selection[0])["values"][0]
        if messagebox.askyesno("Confirm", "Cancel this appointment?", parent=self):
            self._on_cancel(int(appt_id))
