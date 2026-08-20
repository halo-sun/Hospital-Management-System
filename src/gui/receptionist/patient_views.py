"""Patient registration and search views.

All views in this module inherit from ``BaseView`` for consistency
and use ``Theme`` constants for colours and fonts.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime
from typing import Optional, Callable, Dict, Any, List, Tuple

from src.gui.theme import Theme
from src.gui.common.base_view import BaseView
from src.constants import Gender, BloodGroup


# ── Field types for the registration form ─────────────────────

class FieldType:
    """Describes a single field row in a patient form."""
    __slots__ = ("key", "label", "required", "widget_type", "values")

    def __init__(
        self,
        key: str,
        label: str,
        required: bool = False,
        widget_type: str = "entry",
        values: Optional[List[str]] = None,
    ) -> None:
        self.key = key
        self.label = label
        self.required = required
        self.widget_type = widget_type  # "entry" | "combo"
        self.values = values


# Fields shared by both register and edit forms
_PATIENT_FIELDS = [
    FieldType("full_name", "Full Name *", required=True),
    FieldType("date_of_birth", "Date of Birth (DD-MM-YYYY)"),
    FieldType("gender", "Gender", widget_type="combo", values=Gender.ALL),
    FieldType("contact_number", "Contact Number *", required=True),
    FieldType("email", "Email"),
    FieldType("address", "Address"),
    FieldType("blood_group", "Blood Group", widget_type="combo", values=BloodGroup.ALL),
    FieldType("allergies", "Allergies"),
    FieldType("emergency_contact_name", "Emergency Contact Name"),
    FieldType("emergency_contact_number", "Emergency Contact Number"),
]


# ── Registration / Edit form ──────────────────────────────────

class PatientRegistrationView(BaseView):
    """Form for registering or editing a patient."""

    def __init__(
        self,
        parent: tk.Widget,
        on_submit: Callable,
        on_cancel: Optional[Callable] = None,
        edit_data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> None:
        """Initialise the registration form.

        Args:
            parent: Parent tkinter widget.
            on_submit: Callback invoked with form data dict.
            on_cancel: Optional callback for the cancel button.
            edit_data: Optional dict to pre-fill for editing.
        """
        super().__init__(parent, **kwargs)
        self._on_submit = on_submit
        self._on_cancel = on_cancel
        self._edit_data = edit_data or {}
        self._vars: Dict[str, tk.Variable] = {}
        self._build_ui()

    # ── Helpers ────────────────────────────────────────────────

    def _create_field_row(
        self,
        parent: ttk.Frame,
        field: FieldType,
        row: int,
        default: str = "",
    ) -> None:
        """Grid a labelled field row (label + entry or combobox).

        Args:
            parent: The form frame to place the row in.
            field: Field descriptor.
            row: Grid row index.
            default: Default / pre-filled value.
        """
        if field.widget_type == "combo":
            self._vars[field.key] = tk.StringVar(value=default)
            lbl = ttk.Label(parent, text=field.label, font=Theme.FONT_BODY)
            lbl.grid(row=row, column=0, sticky="w", padx=(0, 8), pady=6)
            combo = ttk.Combobox(
                parent, textvariable=self._vars[field.key],
                values=field.values, width=37, state="readonly",
                font=Theme.FONT_BODY,
            )
            combo.grid(row=row, column=1, sticky="ew", pady=6, padx=(0, 16))
        else:
            self._vars[field.key] = tk.StringVar(value=default)
            lbl = ttk.Label(parent, text=field.label, font=Theme.FONT_BODY)
            lbl.grid(row=row, column=0, sticky="w", padx=(0, 8), pady=6)
            entry = ttk.Entry(
                parent, textvariable=self._vars[field.key],
                width=40, font=Theme.FONT_BODY,
            )
            entry.grid(row=row, column=1, sticky="ew", pady=6, padx=(0, 16))

    def _show_age(self, row: int) -> None:
        """Create an age-display label next to the DOB field.

        Listens for changes on the DOB variable and updates the age
        label in real time using the centralised validator.
        """
        from src.utils.validators import validate_date_of_birth

        self._age_label = tk.Label(
            self._form_frame, text="", bg=Theme.BG,
            fg=Theme.MUTED, font=Theme.FONT_SMALL,
        )
        self._age_label.grid(row=row, column=2, sticky="w", padx=(0, 8), pady=6)

        def _on_dob_change(*_: Any) -> None:
            dob = self._vars["date_of_birth"].get()
            valid, msg = validate_date_of_birth(dob)
            if valid and msg:  # msg contains the age string
                self._age_label.config(text=f"Age: {msg}", fg=Theme.SUCCESS)
            elif valid:
                self._age_label.config(text="", fg=Theme.MUTED)
            else:
                # Show error hint but don't block typing
                self._age_label.config(text=msg, fg=Theme.WARNING)

        self._vars["date_of_birth"].trace_add("write", _on_dob_change)

    # ── Build ──────────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Construct the form layout using reusable field rows."""
        is_edit = bool(self._edit_data)
        title = "Edit Patient" if is_edit else "Register New Patient"

        # Header
        header = ttk.Frame(self, style="Header.TFrame", padding=16)
        header.pack(fill="x")
        ttk.Label(header, text=title, style="Heading.TLabel").pack(anchor="w")

        # Scrollable form area
        canvas = tk.Canvas(self, bg=Theme.BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self._form_frame = ttk.Frame(canvas, style="TFrame", padding=24)
        self._form_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self._form_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Build each field row
        for idx, field in enumerate(_PATIENT_FIELDS):
            default = str(self._edit_data.get(field.key, ""))
            self._create_field_row(self._form_frame, field, idx, default)

        # Age label (hooked to DOB changes)
        dob_idx = next(
            i for i, f in enumerate(_PATIENT_FIELDS) if f.key == "date_of_birth"
        )
        self._show_age(dob_idx)

        self._form_frame.columnconfigure(1, weight=1)

        # Buttons
        btn_frame = ttk.Frame(self._form_frame, style="TFrame")
        btn_frame.grid(
            row=len(_PATIENT_FIELDS), column=0, columnspan=2,
            pady=(20, 0), sticky="ew",
        )

        submit_text = "Update Patient" if is_edit else "Register Patient"
        tk.Button(
            btn_frame, text=submit_text, bg=Theme.SUCCESS, fg=Theme.WHITE,
            font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0,
            padx=20, pady=8, command=self._handle_submit,
        ).pack(side="left", padx=(0, 8))

        if self._on_cancel:
            tk.Button(
                btn_frame, text="Cancel", bg=Theme.DANGER, fg=Theme.WHITE,
                font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0,
                padx=20, pady=8, command=self._on_cancel,
            ).pack(side="left")

    # ── Actions ────────────────────────────────────────────────

    def _handle_submit(self) -> None:
        """Collect form data and invoke the submit callback."""
        data = {key: var.get() for key, var in self._vars.items()}
        self._on_submit(data)

    def get_data(self) -> Dict[str, Any]:
        """Return current form data as a dictionary.

        Returns:
            Dictionary of form field values.
        """
        return {key: var.get() for key, var in self._vars.items()}


# ── Search + results table ─────────────────────────────────────

class PatientSearchView(BaseView):
    """Search bar + results table for patients.

    On load the full patient list is displayed immediately.  Typing
    in the search box filters the list live (no button press needed).
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_search: Callable,
        on_select: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_load_all: Optional[Callable[[], List[Dict[str, Any]]]] = None,
        **kwargs,
    ) -> None:
        """Initialise the search view.

        Args:
            parent: Parent tkinter widget.
            on_search: Callback(search_term) for explicit search.
            on_select: Optional callback when a row is selected.
            on_load_all: Optional callback() that returns the full
                patient list for the default view.
        """
        super().__init__(parent, **kwargs)
        self._on_search = on_search
        self._on_select = on_select
        self._on_load_all = on_load_all
        self._all_patients: List[Dict[str, Any]] = []
        self._build_ui()
        self._load_default()

    def _build_ui(self) -> None:
        """Construct the search bar and results table."""
        # ── Header ─────────────────────────────────────────────
        header = ttk.Frame(self, style="Header.TFrame", padding=16)
        header.pack(fill="x")
        ttk.Label(header, text="Search Patients", style="Heading.TLabel").pack(anchor="w")

        # ── Search bar ─────────────────────────────────────────
        search_frame = ttk.Frame(self, style="TFrame", padding=16)
        search_frame.pack(fill="x")

        self._search_var = tk.StringVar()
        entry = ttk.Entry(
            search_frame, textvariable=self._search_var,
            width=40, font=Theme.FONT_BODY,
        )
        entry.pack(side="left", padx=(0, 8))
        entry.bind("<Return>", lambda e: self._do_search())
        # Live search on each keystroke
        self._search_var.trace_add("write", lambda *_: self._on_search_changed())
        self._after_id: Optional[str] = None

        tk.Button(
            search_frame, text="Search", bg=Theme.ACCENT, fg=Theme.WHITE,
            font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0,
            padx=16, pady=6, command=self._do_search,
        ).pack(side="left")

        tk.Button(
            search_frame, text="Clear", bg=Theme.LIGHT, fg=Theme.DARK_TEXT,
            font=Theme.FONT_SMALL_BOLD, cursor="hand2", bd=0,
            padx=10, pady=2, command=self._clear_search,
        ).pack(side="left", padx=(8, 0))

        # ── Results table (using BaseView helper) ──────────────
        table_frame = ttk.Frame(self, style="TFrame", padding=(16, 0))
        table_frame.pack(fill="both", expand=True)

        columns = ("patient_id", "full_name", "contact_number", "gender", "email")
        headings = ("Patient ID", "Full Name", "Phone", "Gender", "Email")

        self._tree = self.create_treeview(
            table_frame, columns=columns, headings=headings,
        )
        self._tree.column("patient_id", width=120, anchor="center")
        self._tree.column("full_name", width=200)
        self._tree.column("contact_number", width=140)
        self._tree.column("gender", width=80, anchor="center")
        self._tree.column("email", width=180)

        if self._on_select:
            self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    def _load_default(self) -> None:
        """Load the full patient list on initial display."""
        if self._on_load_all:
            try:
                self._all_patients = self._on_load_all()
            except Exception:
                self._all_patients = []
            self.populate(self._all_patients)

    def _on_search_changed(self) -> None:
        """Debounced live search — filters on each keystroke."""
        if self._after_id is not None:
            self.after_cancel(self._after_id)
        self._after_id = self.after(200, self._do_search)

    def _do_search(self) -> None:
        """Execute the search and update the table."""
        self._after_id = None
        term = self._search_var.get().strip()
        if not term:
            # Empty search → show full list
            self.populate(self._all_patients)
            return
        if len(term) < 2:
            # Too short for backend search — filter client-side
            term_lower = term.lower()
            filtered = [
                p for p in self._all_patients
                if term_lower in (p.get("patient_id", "")).lower()
                or term_lower in (p.get("full_name", "")).lower()
                or term_lower in (p.get("contact_number", "")).lower()
            ]
            self.populate(filtered)
            return
        # Use backend search for 2+ characters (LIKE query)
        self._on_search(term)

    def _clear_search(self) -> None:
        """Reset the search and show the full list."""
        self._search_var.set("")

    def _on_tree_select(self, event: tk.Event) -> None:
        """Handle tree selection."""
        selection = self._tree.selection()
        if selection and self._on_select:
            item = self._tree.item(selection[0])
            self._on_select(dict(zip(self._tree["columns"], item["values"])))

    def populate(self, patients: List[Dict[str, Any]]) -> None:
        """Fill the tree with patient records.

        Args:
            patients: List of patient dictionaries.
        """
        self._tree.delete(*self._tree.get_children())
        for p in patients:
            self._tree.insert("", "end", values=(
                p.get("patient_id", ""),
                p.get("full_name", ""),
                p.get("contact_number", ""),
                p.get("gender", ""),
                p.get("email", ""),
            ))
        self.apply_default_sort(self._tree)
