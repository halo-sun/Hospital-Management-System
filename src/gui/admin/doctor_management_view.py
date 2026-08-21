"""Admin doctor management view with search and filtering.

Independent from other modules — single responsibility: display
and filter doctors in a table with CRUD actions.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable, Dict, Any, List
from src.gui.theme import Theme
from src.gui.common.base_view import BaseView
from src.constants import DoctorStatus


class DoctorManagementView(BaseView):
    """Table view for managing doctors with search and filtering."""

    def __init__(
        self,
        parent: tk.Widget,
        doctors: List[Dict[str, Any]],
        departments: List[Dict[str, Any]],
        specializations: Optional[List[str]] = None,
        on_search: Optional[Callable] = None,
        on_filter: Optional[Callable] = None,
        on_add: Optional[Callable] = None,
        on_edit: Optional[Callable[[int], None]] = None,
        on_delete: Optional[Callable[[int], None]] = None,
        on_schedule: Optional[Callable[[int], None]] = None,
        on_leave: Optional[Callable[[int], None]] = None,
        on_refresh: Optional[Callable] = None,
        initial_department: Optional[str] = None,
        initial_specialization: Optional[str] = None,
        initial_status: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Initialise the doctor management view.

        Args:
            parent: Parent tkinter widget.
            doctors: List of doctor dicts (full unfiltered list).
            departments: List of department dicts.
            specializations: Optional list of all known specializations.
            on_search: Callback(search_term) for text search.
            on_filter: Callback(department_id, specialization, status) for filtering.
            on_add: Callback to add a doctor.
            on_edit: Callback to edit a doctor.
            on_delete: Callback to delete a doctor.
            on_schedule: Callback to manage a doctor's schedule.
            on_refresh: Callback to refresh the list.
            initial_department: Pre-selected department name (for restored state).
            initial_specialization: Pre-selected specialization.
            initial_status: Pre-selected status.
        """
        super().__init__(parent, **kwargs)
        self._all_doctors = list(doctors)
        self._departments = departments
        self._specializations = specializations or []
        self._on_search = on_search
        self._on_filter = on_filter
        self._on_add = on_add
        self._on_edit = on_edit
        self._on_delete = on_delete
        self._on_schedule = on_schedule
        self._on_leave = on_leave
        self._on_refresh = on_refresh
        self._initial_department = initial_department
        self._initial_specialization = initial_specialization
        self._initial_status = initial_status
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the doctor management layout."""
        # ── Header ─────────────────────────────────────────────────
        header = ttk.Frame(self, style="Header.TFrame", padding=16)
        header.pack(fill="x")

        ttk.Label(header, text="Doctor Management", style="Heading.TLabel").pack(side="left")

        if self._on_add:
            tk.Button(
                header, text="+ Add Doctor", bg=Theme.SUCCESS, fg=Theme.WHITE,
                font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=12, pady=4,
                command=self._on_add,
            ).pack(side="right", padx=4)

        if self._on_refresh:
            tk.Button(
                header, text="Refresh", bg=Theme.ACCENT, fg=Theme.WHITE,
                font=Theme.FONT_SMALL, cursor="hand2", bd=0, padx=12, pady=4,
                command=self._on_refresh,
            ).pack(side="right", padx=4)

        # ── Stats summary ─────────────────────────────────────────
        stats_frame = ttk.Frame(self, style="TFrame", padding=(16, 8))
        stats_frame.pack(fill="x")
        active = sum(1 for d in self._all_doctors if d.get("status") == DoctorStatus.ACTIVE)
        total = len(self._all_doctors)
        ttk.Label(
            stats_frame,
            text=f"Total Doctors: {total}  |  Active: {active}",
            style="Subheading.TLabel",
        ).pack(anchor="w")

        # ── Search + Filter bar ────────────────────────────────────
        filter_frame = ttk.Frame(self, style="TFrame", padding=(16, 4))
        filter_frame.pack(fill="x")

        # Search entry
        ttk.Label(filter_frame, text="Search:", font=Theme.FONT_BODY).pack(side="left", padx=(0, 4))
        self._search_var = tk.StringVar()
        search_entry = ttk.Entry(
            filter_frame, textvariable=self._search_var,
            width=25, font=Theme.FONT_BODY,
        )
        search_entry.pack(side="left", padx=(0, 8))
        search_entry.bind("<Return>", lambda e: self._do_search())

        tk.Button(
            filter_frame, text="Search", bg=Theme.ACCENT, fg=Theme.WHITE,
            font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=10, pady=2,
            command=self._do_search,
        ).pack(side="left", padx=(0, 16))

        # Department filter
        ttk.Label(filter_frame, text="Department:", font=Theme.FONT_BODY).pack(side="left", padx=(0, 4))
        self._dept_filter_var = tk.StringVar()
        dept_names = ["All"] + [d.get("department_name", "") for d in self._departments]
        dept_combo = ttk.Combobox(
            filter_frame, textvariable=self._dept_filter_var,
            values=dept_names, width=18, state="readonly", font=Theme.FONT_BODY,
        )
        dept_combo.current(0)
        dept_combo.pack(side="left", padx=(0, 12))
        dept_combo.bind("<<ComboboxSelected>>", lambda e: self._do_filter())

        # Specialization filter
        ttk.Label(filter_frame, text="Specialization:", font=Theme.FONT_BODY).pack(side="left", padx=(0, 4))
        self._spec_filter_var = tk.StringVar()
        spec_names = ["All"] + self._specializations
        spec_combo = ttk.Combobox(
            filter_frame, textvariable=self._spec_filter_var,
            values=spec_names, width=18, state="readonly", font=Theme.FONT_BODY,
        )
        spec_combo.current(0)
        spec_combo.pack(side="left", padx=(0, 12))
        spec_combo.bind("<<ComboboxSelected>>", lambda e: self._do_filter())

        # Status filter
        ttk.Label(filter_frame, text="Status:", font=Theme.FONT_BODY).pack(side="left", padx=(0, 4))
        self._status_filter_var = tk.StringVar()
        status_names = ["All", DoctorStatus.ACTIVE, DoctorStatus.INACTIVE, DoctorStatus.ON_LEAVE]
        status_combo = ttk.Combobox(
            filter_frame, textvariable=self._status_filter_var,
            values=status_names, width=12, state="readonly", font=Theme.FONT_BODY,
        )
        status_combo.current(0)
        status_combo.pack(side="left", padx=(0, 12))
        status_combo.bind("<<ComboboxSelected>>", lambda e: self._do_filter())

        # Clear filters button
        tk.Button(
            filter_frame, text="Clear Filters", bg=Theme.LIGHT, fg=Theme.DARK_TEXT,
            font=Theme.FONT_SMALL_BOLD, cursor="hand2", bd=0, padx=10, pady=2,
            command=self._clear_filters,
        ).pack(side="left")

        # ── Table ─────────────────────────────────────────────────
        table_frame = ttk.Frame(self, style="TFrame", padding=16)
        table_frame.pack(fill="both", expand=True)

        columns = ("id", "name", "department", "specialization", "email", "phone", "status")
        self._tree = self.create_treeview(
            table_frame, columns=columns,
            headings=("ID", "Name", "Department", "Specialization", "Email", "Phone", "Status"),
        )
        self._tree.column("id", width=50, anchor="center")
        self._tree.column("name", width=160)
        self._tree.column("department", width=130)
        self._tree.column("specialization", width=140)
        self._tree.column("email", width=170)
        self._tree.column("phone", width=120)
        self._tree.column("status", width=80, anchor="center")

        # Restore initial filter selections (if any) before populating
        if self._initial_department:
            self._dept_filter_var.set(self._initial_department)
        if self._initial_specialization:
            self._spec_filter_var.set(self._initial_specialization)
        if self._initial_status:
            self._status_filter_var.set(self._initial_status)

        self.populate(self._all_doctors)

        # ── Action buttons ────────────────────────────────────────
        btn_frame = ttk.Frame(self, style="TFrame", padding=(16, 0, 16, 16))
        btn_frame.pack(fill="x")

        if self._on_edit:
            tk.Button(
                btn_frame, text="Edit", bg=Theme.WARNING, fg=Theme.WHITE,
                font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=12, pady=6,
                command=self._handle_edit,
            ).pack(side="left", padx=(0, 8))

        if self._on_schedule:
            tk.Button(
                btn_frame, text="Schedule", bg=Theme.ACCENT, fg=Theme.WHITE,
                font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=12, pady=6,
                command=self._handle_schedule,
            ).pack(side="left", padx=(0, 8))

        if self._on_leave:
            tk.Button(
                btn_frame, text="Add Leave", bg=Theme.WARNING, fg=Theme.WHITE,
                font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=12, pady=6,
                command=self._handle_leave,
            ).pack(side="left", padx=(0, 8))

        if self._on_delete:
            tk.Button(
                btn_frame, text="Delete", bg=Theme.DANGER, fg=Theme.WHITE,
                font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=12, pady=6,
                command=self._handle_delete,
            ).pack(side="left")

    # ── Public API ─────────────────────────────────────────────

    def populate(self, doctors: List[Dict[str, Any]]) -> None:
        """Fill the tree with doctor records and apply active filters.

        Stores the full doctor list for client-side filtering.

        Args:
            doctors: List of doctor dictionaries.
        """
        self._all_doctors = list(doctors)
        self._apply_filters()

    def update_specializations(self, specializations: List[str]) -> None:
        """Update the specialization filter dropdown.

        Args:
            specializations: List of specialization strings.
        """
        self._specializations = specializations

    # ── Internal handlers ─────────────────────────────────────

    def _do_search(self) -> None:
        """Execute the search callback."""
        if self._on_search:
            term = self._search_var.get().strip()
            self._on_search(term)

    def _apply_filters(self) -> None:
        """Apply all active filters client-side and repopulate the tree.

        Reads the current search term and dropdown selections, filters
        ``_all_doctors`` accordingly (AND logic), and re-renders the
        tree with the matching subset.  This runs on every dropdown
        change and on initial load, so filters always compose correctly
        with the default ID-ascending sort.
        """
        dept_name = self._dept_filter_var.get()
        spec = self._spec_filter_var.get()
        status = self._status_filter_var.get()
        search_term = self._search_var.get().strip().lower()

        filtered = list(self._all_doctors)

        # Department filter
        if dept_name and dept_name != "All":
            filtered = [
                d for d in filtered
                if d.get("department_name") == dept_name
            ]

        # Specialization filter (substring match)
        if spec and spec != "All":
            spec_lower = spec.lower()
            filtered = [
                d for d in filtered
                if d.get("specialization")
                and spec_lower in d["specialization"].lower()
            ]

        # Status filter
        if status and status != "All":
            filtered = [
                d for d in filtered
                if d.get("status", "").lower() == status.lower()
            ]

        # Text search filter
        if search_term:
            filtered = [
                d for d in filtered
                if search_term in d.get("full_name", "").lower()
                or search_term in d.get("department_name", "").lower()
                or search_term in d.get("specialization", "").lower()
                or search_term in d.get("email", "").lower()
                or search_term in (d.get("contact_number") or "").lower()
            ]

        self._tree.delete(*self._tree.get_children())
        for d in filtered:
            self._tree.insert("", "end", values=(
                d.get("doctor_id", ""),
                d.get("full_name", ""),
                d.get("department_name", ""),
                d.get("specialization", ""),
                d.get("email", ""),
                d.get("contact_number", ""),
                d.get("status", ""),
            ), iid=str(d.get("doctor_id", "")))
        self.apply_default_sort(self._tree)

    def _do_filter(self) -> None:
        """Re-apply filters when a dropdown selection changes."""
        self._apply_filters()

    def _clear_filters(self) -> None:
        """Reset all filters and show the full list."""
        self._search_var.set("")
        self._dept_filter_var.set("All")
        self._spec_filter_var.set("All")
        self._status_filter_var.set("All")
        self._apply_filters()

    def _handle_edit(self) -> None:
        """Edit the selected doctor."""
        selection = self._tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a doctor.", parent=self)
            return
        self._on_edit(int(selection[0]))

    def _handle_schedule(self) -> None:
        """Manage schedule for the selected doctor."""
        selection = self._tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a doctor.", parent=self)
            return
        self._on_schedule(int(selection[0]))

    def _handle_leave(self) -> None:
        """Add leave for the selected doctor."""
        selection = self._tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a doctor.", parent=self)
            return
        self._on_leave(int(selection[0]))

    def _handle_delete(self) -> None:
        """Delete the selected doctor."""
        selection = self._tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a doctor.", parent=self)
            return
        doctor_id = int(selection[0])
        if messagebox.askyesno("Confirm", "Delete this doctor?\n\nThis action cannot be undone.", parent=self):
            self._on_delete(doctor_id)


class DoctorFormView(BaseView):
    """Form for adding/editing a doctor."""

    def __init__(
        self,
        parent: tk.Widget,
        departments: List[Dict[str, Any]],
        on_submit: Callable,
        on_cancel: Optional[Callable] = None,
        edit_data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> None:
        """Initialise the doctor form.

        Args:
            parent: Parent tkinter widget.
            departments: List of department dicts.
            on_submit: Callback invoked with form data dict.
            on_cancel: Optional cancel callback.
            edit_data: Optional dict to pre-fill for editing.
        """
        super().__init__(parent, **kwargs)
        self._departments = departments
        self._on_submit = on_submit
        self._on_cancel = on_cancel
        self._edit_data = edit_data
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the form layout."""
        is_edit = self._edit_data is not None
        title = "Edit Doctor" if is_edit else "Add New Doctor"

        header = ttk.Frame(self, style="Header.TFrame", padding=16)
        header.pack(fill="x")
        ttk.Label(header, text=title, style="Heading.TLabel").pack(anchor="w")

        canvas = tk.Canvas(self, bg=Theme.BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        form = ttk.Frame(canvas, style="TFrame", padding=24)
        form.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=form, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        form.columnconfigure(1, weight=1)

        self._vars: Dict[str, tk.StringVar] = {}
        row = 0

        # Helper to create a field row
        def _field(label: str, key: str, row_num: int, show: Optional[str] = None) -> int:
            default = str(self._edit_data.get(key, "")) if self._edit_data else ""
            self._vars[key] = tk.StringVar(value=default)
            ttk.Label(form, text=label, font=Theme.FONT_BODY).grid(
                row=row_num, column=0, sticky="w", padx=(0, 8), pady=5
            )
            ttk.Entry(form, textvariable=self._vars[key], width=40, font=Theme.FONT_BODY, show=show).grid(
                row=row_num, column=1, sticky="ew", pady=5
            )
            return row_num + 1

        # Full name
        row = _field("Full Name *", "full_name", row)

        # Department
        default_dept = self._edit_data.get("department_name", "") if self._edit_data else ""
        self._vars["department_name"] = tk.StringVar(value=default_dept)
        ttk.Label(form, text="Department *", font=Theme.FONT_BODY).grid(
            row=row, column=0, sticky="w", padx=(0, 8), pady=5
        )
        dept_combo = ttk.Combobox(
            form, textvariable=self._vars["department_name"],
            values=[d.get("department_name", "") for d in self._departments],
            width=37, state="readonly", font=Theme.FONT_BODY,
        )
        dept_combo.grid(row=row, column=1, sticky="ew", pady=5)
        row += 1

        # Specialization
        row = _field("Specialization", "specialization", row)

        # Email
        row = _field("Email", "email", row)

        # Phone
        row = _field("Phone", "contact_number", row)

        # Qualification
        row = _field("Qualification", "qualification", row)

        # Experience
        default_exp = str(self._edit_data.get("experience_years", 0)) if self._edit_data else "0"
        self._vars["experience_years"] = tk.StringVar(value=default_exp)
        ttk.Label(form, text="Experience (years)", font=Theme.FONT_BODY).grid(
            row=row, column=0, sticky="w", padx=(0, 8), pady=5
        )
        ttk.Entry(form, textvariable=self._vars["experience_years"], width=40, font=Theme.FONT_BODY).grid(
            row=row, column=1, sticky="ew", pady=5
        )
        row += 1

        # Consultation fee
        default_fee = str(self._edit_data.get("consultation_fee", 0)) if self._edit_data else "0"
        self._vars["consultation_fee"] = tk.StringVar(value=default_fee)
        ttk.Label(form, text="Consultation Fee", font=Theme.FONT_BODY).grid(
            row=row, column=0, sticky="w", padx=(0, 8), pady=5
        )
        ttk.Entry(form, textvariable=self._vars["consultation_fee"], width=40, font=Theme.FONT_BODY).grid(
            row=row, column=1, sticky="ew", pady=5
        )
        row += 1

        # Username / Password (only for new)
        if not is_edit:
            row = _field("Login Username *", "username", row)
            row = _field("Login Password *", "password", row, show="*")

        # Working hours (for new doctors)
        if not is_edit:
            row = _field("Working Hours Start (HH:MM)", "working_hours_start", row)
            row = _field("Working Hours End (HH:MM)", "working_hours_end", row)

        # Buttons
        btn_frame = ttk.Frame(form, style="TFrame")
        btn_frame.grid(row=row, column=0, columnspan=2, pady=(20, 0), sticky="ew")

        submit_text = "Update Doctor" if is_edit else "Add Doctor"
        tk.Button(
            btn_frame, text=submit_text, bg=Theme.SUCCESS, fg=Theme.WHITE,
            font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=20, pady=8,
            command=self._handle_submit,
        ).pack(side="left", padx=(0, 8))

        if self._on_cancel:
            tk.Button(
                btn_frame, text="Cancel", bg=Theme.DANGER, fg=Theme.WHITE,
                font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=20, pady=8,
                command=self._on_cancel,
            ).pack(side="left")

    def _handle_submit(self) -> None:
        """Collect form data and invoke the submit callback."""
        data = {key: var.get() for key, var in self._vars.items()}
        # Resolve department_id from name
        dept_name = data.pop("department_name", "")
        for d in self._departments:
            if d.get("department_name") == dept_name:
                data["department_id"] = d.get("department_id")
                break
        self._on_submit(data)
