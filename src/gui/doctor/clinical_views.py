"""Clinical records GUI — visit forms, patient timeline, prescriptions, reports.

All views inherit from ``BaseView`` and use ``Theme`` constants so that
the look stays consistent with the rest of the application.
"""
from __future__ import annotations

import logging
import os
from datetime import date
from tkinter import filedialog, messagebox
from typing import Any, Callable, Dict, List, Optional, Tuple

import tkinter as tk
from tkinter import ttk

from src.gui.theme import Theme
from src.gui.common.base_view import BaseView
from src.constants import ReportType

logger = logging.getLogger(__name__)


# ── Clinical Records (main landing) ───────────────────────────

class ClinicalRecordsView(BaseView):
    """Main clinical records view with patient search and visit history.

    Shows a patient search bar on the left and the selected patient's
    visit timeline on the right.
    """

    def __init__(
        self,
        parent: tk.Widget,
        doctor_id: int,
        on_search: Callable[[str], List[Dict[str, Any]]],
        on_patient_selected: Callable[[str], None],
        on_create_visit: Callable[[int, str], None],
        on_view_visit: Callable[[int], None],
        **kwargs,
    ) -> None:
        """Initialise the clinical records view.

        Args:
            parent: Parent tkinter widget.
            doctor_id: The logged-in doctor's ID.
            on_search: Callback(search_term) → list of matching visit dicts.
            on_patient_selected: Callback(patient_id) when a patient is chosen.
            on_create_visit: Callback(visit_id, patient_id) to open visit form.
            on_view_visit: Callback(visit_id) to open visit detail.
        """
        super().__init__(parent, **kwargs)
        self._doctor_id = doctor_id
        self._on_search = on_search
        self._on_patient_selected = on_patient_selected
        self._on_create_visit = on_create_visit
        self._on_view_visit = on_view_visit
        self._patients: List[Dict[str, Any]] = []
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the clinical records layout."""
        # ── Header ──────────────────────────────────────────────
        header = ttk.Frame(self, style="Header.TFrame", padding=16)
        header.pack(fill="x")
        ttk.Label(header, text="Clinical Records", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(
            header, text="Search patients and manage visit records",
            style="Subheading.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        # ── Main content (search + detail panes) ────────────────
        main = ttk.Frame(self, style="TFrame")
        main.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        main.columnconfigure(0, weight=1, uniform="pane")
        main.columnconfigure(1, weight=2, uniform="pane")
        main.rowconfigure(0, weight=1)

        # ── Left pane — patient search ─────────────────────────
        left_pane = ttk.LabelFrame(main, text="Patient Search", padding=8)
        left_pane.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left_pane.columnconfigure(0, weight=1)
        left_pane.rowconfigure(1, weight=1)

        self._search_var = tk.StringVar()
        search_entry = ttk.Entry(
            left_pane, textvariable=self._search_var,
            width=30, font=Theme.FONT_BODY,
        )
        search_entry.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        search_entry.bind("<Return>", lambda e: self._do_search())

        tk.Button(
            left_pane, text="Search", bg=Theme.ACCENT, fg=Theme.WHITE,
            font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0,
            padx=10, pady=2, command=self._do_search,
        ).grid(row=0, column=1, padx=(4, 0))

        columns = ("patient_id", "patient_name", "visits")
        self._patient_tree = ttk.Treeview(
            left_pane, columns=columns, show="headings", height=20,
        )
        self._patient_tree.heading("patient_id", text="Patient ID")
        self._patient_tree.heading("patient_name", text="Name")
        self._patient_tree.heading("visits", text="Visits")
        self._patient_tree.column("patient_id", width=100, anchor="center")
        self._patient_tree.column("patient_name", width=150)
        self._patient_tree.column("visits", width=60, anchor="center")
        self._patient_tree.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self._patient_tree.bind("<<TreeviewSelect>>", self._on_patient_tree_select)

        vsb = ttk.Scrollbar(left_pane, orient="vertical", command=self._patient_tree.yview)
        self._patient_tree.configure(yscrollcommand=vsb.set)
        vsb.grid(row=1, column=2, sticky="ns")

        # ── Right pane — timeline / detail ─────────────────────
        right_pane = ttk.LabelFrame(main, text="Visit History", padding=8)
        right_pane.grid(row=0, column=1, sticky="nsew")
        right_pane.columnconfigure(0, weight=1)
        right_pane.rowconfigure(0, weight=1)

        self._timeline_frame = ttk.Frame(right_pane, style="TFrame")
        self._timeline_frame.grid(row=0, column=0, sticky="nsew")
        self._timeline_frame.columnconfigure(0, weight=1)
        self._timeline_frame.rowconfigure(0, weight=1)

        # Placeholder shown until a patient is selected
        self._placeholder = ttk.Label(
            self._timeline_frame, text="Select a patient to view visit history",
            style="TLabel",
        )
        self._placeholder.grid(row=0, column=0, pady=40)

    # ── Public API ─────────────────────────────────────────────

    def set_patients(self, patients: List[Dict[str, Any]]) -> None:
        """Update the patient list.

        Args:
            patients: List of patient dicts (patient_id, patient_name, count).
        """
        self._patients = patients
        self._patient_tree.delete(*self._patient_tree.get_children())
        for p in patients:
            self._patient_tree.insert("", "end", values=(
                p.get("patient_id", ""),
                p.get("patient_name", p.get("full_name", "")),
                p.get("visit_count", p.get("count", 0)),
            ))

    def show_timeline(self, visits: List[Dict[str, Any]]) -> None:
        """Display the timeline for the selected patient.

        Args:
            visits: List of visit records with prescriptions and reports.
        """
        self._clear_timeline()

        if not visits:
            ttk.Label(
                self._timeline_frame, text="No visit records found for this patient.",
                style="TLabel",
            ).pack(pady=40)
            return

        # Scrollable timeline
        canvas = tk.Canvas(self._timeline_frame, bg=Theme.SURFACE, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self._timeline_frame, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas, style="TFrame")
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for idx, visit in enumerate(visits):
            self._create_visit_card(scroll_frame, visit, idx)

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

    # ── Internal helpers ───────────────────────────────────────

    def _clear_timeline(self) -> None:
        """Remove all timeline widgets."""
        for w in self._timeline_frame.winfo_children():
            w.destroy()

    def _create_visit_card(
        self, parent: ttk.Frame, visit: Dict[str, Any], idx: int,
    ) -> None:
        """Create a timeline card for a single visit.

        Args:
            parent: Parent frame.
            visit: Visit record dict.
            idx: Index for alternating background.
        """
        card = ttk.Frame(
            parent, style="Card.TFrame", padding=12,
        )
        card.pack(fill="x", padx=8, pady=(0, 8))

        # Date header
        visit_date = visit.get("visit_date", "")
        if hasattr(visit_date, "strftime"):
            visit_date = visit_date.strftime("%b %d, %Y")

        header_frame = ttk.Frame(card, style="Card.TFrame")
        header_frame.pack(fill="x")

        ttk.Label(
            header_frame, text=f"Visit #{visit.get('visit_id', '')}",
            style="Subheading.TLabel",
        ).pack(side="left")

        ttk.Label(
            header_frame, text=visit_date,
            style="TLabel",
        ).pack(side="right")

        # Diagnosis (if available)
        diagnosis = visit.get("diagnosis", "")
        if diagnosis:
            ttk.Label(
                card, text=f"Diagnosis: {diagnosis}",
                style="Card.TLabel", wraplength=400,
            ).pack(anchor="w", pady=(4, 0))

        # Doctor notes (if available)
        notes = visit.get("doctor_notes", "")
        if notes:
            ttk.Label(
                card, text=f"Notes: {notes[:100]}{'...' if len(notes) > 100 else ''}",
                style="Card.TLabel", wraplength=400,
            ).pack(anchor="w")

        # Prescriptions summary
        prescriptions = visit.get("prescriptions", [])
        if prescriptions:
            rx_text = "; ".join(
                f"{p.get('medicine_name', '')} ({p.get('dosage', '')})"
                for p in prescriptions[:3]
            )
            if len(prescriptions) > 3:
                rx_text += f" ... (+{len(prescriptions) - 3} more)"
            ttk.Label(
                card, text=f"Rx: {rx_text}",
                style="Card.TLabel", wraplength=400,
            ).pack(anchor="w")

        # Reports count
        reports = visit.get("reports", [])
        if reports:
            ttk.Label(
                card, text=f"Reports: {len(reports)} file(s)",
                style="Card.TLabel",
            ).pack(anchor="w")

        # View button
        visit_id = visit.get("visit_id", 0)
        tk.Button(
            card, text="View Details", bg=Theme.ACCENT, fg=Theme.WHITE,
            font=Theme.FONT_SMALL_BOLD, cursor="hand2", bd=0,
            padx=10, pady=2,
            command=lambda vid=visit_id: self._on_view_visit(vid),
        ).pack(anchor="e", pady=(4, 0))

    def _do_search(self) -> None:
        """Execute the patient search."""
        term = self._search_var.get().strip()
        if term:
            self._on_search(term)

    def _on_patient_tree_select(self, event: tk.Event) -> None:
        """Handle patient selection from tree."""
        selection = self._patient_tree.selection()
        if selection:
            item = self._patient_tree.item(selection[0])
            values = item["values"]
            if values and len(values) > 0:
                self._on_patient_selected(str(values[0]))


# ── Visit Form ─────────────────────────────────────────────────

class VisitFormView(BaseView):
    """Form for creating or editing a visit record."""

    def __init__(
        self,
        parent: tk.Widget,
        patient_id: str,
        patient_name: str,
        doctor_id: int,
        on_submit: Callable[[Dict[str, Any]], None],
        on_cancel: Optional[Callable] = None,
        edit_data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> None:
        """Initialise the visit form.

        Args:
            parent: Parent tkinter widget.
            patient_id: The patient ID.
            patient_name: The patient's name for display.
            doctor_id: The doctor ID.
            on_submit: Callback invoked with form data dict.
            on_cancel: Optional cancel callback.
            edit_data: Optional dict to pre-fill for editing.
        """
        super().__init__(parent, **kwargs)
        self._patient_id = patient_id
        self._patient_name = patient_name
        self._doctor_id = doctor_id
        self._on_submit = on_submit
        self._on_cancel = on_cancel
        self._edit_data = edit_data or {}
        self._vars: Dict[str, tk.Variable] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the visit form layout."""
        is_edit = bool(self._edit_data)
        title = "Edit Visit Record" if is_edit else "New Visit Record"

        # ── Header ─────────────────────────────────────────────
        header = ttk.Frame(self, style="Header.TFrame", padding=16)
        header.pack(fill="x")
        ttk.Label(header, text=title, style="Heading.TLabel").pack(anchor="w")
        ttk.Label(
            header, text=f"Patient: {self._patient_id} - {self._patient_name}",
            style="Subheading.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        # ── Form ───────────────────────────────────────────────
        form = ttk.Frame(self, style="TFrame", padding=24)
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)

        row = 0

        # Visit date
        default_date = str(self._edit_data.get("visit_date", date.today()))
        if hasattr(default_date, "strftime"):
            default_date = default_date.strftime("%Y-%m-%d")
        self._add_text_field(form, "Visit Date (YYYY-MM-DD)", "visit_date", row, default=default_date)
        row += 1

        # Symptoms (multi-line)
        ttk.Label(form, text="Symptoms", font=Theme.FONT_BODY).grid(
            row=row, column=0, sticky="nw", padx=(0, 8), pady=6,
        )
        self._symptoms_text = tk.Text(form, height=4, width=50, font=Theme.FONT_BODY, bg=Theme.SURFACE, fg=Theme.DARK_TEXT, insertbackground=Theme.DARK_TEXT)
        self._symptoms_text.grid(row=row, column=1, sticky="ew", pady=6)
        if self._edit_data.get("symptoms"):
            self._symptoms_text.insert("1.0", self._edit_data["symptoms"])
        row += 1

        # Diagnosis (multi-line)
        ttk.Label(form, text="Diagnosis", font=Theme.FONT_BODY).grid(
            row=row, column=0, sticky="nw", padx=(0, 8), pady=6,
        )
        self._diagnosis_text = tk.Text(form, height=4, width=50, font=Theme.FONT_BODY, bg=Theme.SURFACE, fg=Theme.DARK_TEXT, insertbackground=Theme.DARK_TEXT)
        self._diagnosis_text.grid(row=row, column=1, sticky="ew", pady=6)
        if self._edit_data.get("diagnosis"):
            self._diagnosis_text.insert("1.0", self._edit_data["diagnosis"])
        row += 1

        # Doctor notes (multi-line)
        ttk.Label(form, text="Doctor Notes", font=Theme.FONT_BODY).grid(
            row=row, column=0, sticky="nw", padx=(0, 8), pady=6,
        )
        self._notes_text = tk.Text(form, height=6, width=50, font=Theme.FONT_BODY, bg=Theme.SURFACE, fg=Theme.DARK_TEXT, insertbackground=Theme.DARK_TEXT)
        self._notes_text.grid(row=row, column=1, sticky="ew", pady=6)
        if self._edit_data.get("doctor_notes"):
            self._notes_text.insert("1.0", self._edit_data["doctor_notes"])
        row += 1

        # Follow-up date
        default_fu = str(self._edit_data.get("follow_up_date", ""))
        if hasattr(default_fu, "strftime"):
            default_fu = default_fu.strftime("%Y-%m-%d")
        self._add_text_field(form, "Follow-up Date (YYYY-MM-DD, optional)", "follow_up_date", row, default=default_fu)
        row += 1

        # Buttons
        btn_frame = ttk.Frame(form, style="TFrame")
        btn_frame.grid(row=row, column=0, columnspan=2, pady=(20, 0), sticky="ew")

        submit_text = "Update Visit" if is_edit else "Save Visit Record"
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

    def _add_text_field(
        self, parent: ttk.Frame, label: str, key: str, row: int, default: str = "",
    ) -> ttk.Entry:
        """Add a single-line text field row.

        Args:
            parent: Parent frame.
            label: Label text.
            key: Data key.
            row: Grid row.
            default: Default value.

        Returns:
            The created Entry widget.
        """
        self._vars[key] = tk.StringVar(value=default)
        ttk.Label(parent, text=label, font=Theme.FONT_BODY).grid(
            row=row, column=0, sticky="w", padx=(0, 8), pady=6,
        )
        entry = ttk.Entry(parent, textvariable=self._vars[key], width=50, font=Theme.FONT_BODY)
        entry.grid(row=row, column=1, sticky="ew", pady=6)
        return entry

    def _handle_submit(self) -> None:
        """Collect form data and invoke the submit callback."""
        data = {key: var.get() for key, var in self._vars.items()}
        data["symptoms"] = self._symptoms_text.get("1.0", tk.END).strip()
        data["diagnosis"] = self._diagnosis_text.get("1.0", tk.END).strip()
        data["doctor_notes"] = self._notes_text.get("1.0", tk.END).strip()
        self._on_submit(data)


# ── Prescription Form Dialog ───────────────────────────────────

class PrescriptionFormDialog(tk.Toplevel):
    """Modal dialog for adding a prescription."""

    def __init__(
        self,
        parent: tk.Widget,
        on_submit: Callable[[Dict[str, str]], None],
        edit_data: Optional[Dict[str, str]] = None,
    ) -> None:
        """Initialise the prescription dialog.

        Args:
            parent: Parent widget.
            on_submit: Callback invoked with prescription data.
            edit_data: Optional dict to pre-fill for editing.
        """
        super().__init__(parent)
        self._on_submit = on_submit
        self._edit_data = edit_data or {}
        self._vars: Dict[str, tk.StringVar] = {}

        self.title("Edit Prescription" if edit_data else "Add Prescription")
        self.configure(bg=Theme.BG)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self.update_idletasks()

        # Center on parent
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _build_ui(self) -> None:
        """Construct the dialog layout."""
        form = ttk.Frame(self, style="TFrame", padding=16)
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)

        fields = [
            ("medicine_name", "Medicine Name *", True),
            ("dosage", "Dosage (e.g. 500mg)", False),
            ("frequency", "Frequency (e.g. Twice daily)", False),
            ("duration", "Duration (e.g. 7 days)", False),
        ]

        for idx, (key, label, required) in enumerate(fields):
            default = self._edit_data.get(key, "")
            self._vars[key] = tk.StringVar(value=default)
            lbl_text = label
            ttk.Label(form, text=lbl_text, font=Theme.FONT_BODY).grid(
                row=idx, column=0, sticky="w", padx=(0, 8), pady=6,
            )
            ttk.Entry(form, textvariable=self._vars[key], width=40, font=Theme.FONT_BODY).grid(
                row=idx, column=1, sticky="ew", pady=6,
            )

        # Instructions (multi-line)
        row = len(fields)
        ttk.Label(form, text="Instructions", font=Theme.FONT_BODY).grid(
            row=row, column=0, sticky="nw", padx=(0, 8), pady=6,
        )
        self._instructions_text = tk.Text(form, height=3, width=38, font=Theme.FONT_BODY, bg=Theme.SURFACE, fg=Theme.DARK_TEXT, insertbackground=Theme.DARK_TEXT)
        self._instructions_text.grid(row=row, column=1, sticky="ew", pady=6)
        if self._edit_data.get("instructions"):
            self._instructions_text.insert("1.0", self._edit_data["instructions"])
        row += 1

        # Buttons
        btn_frame = ttk.Frame(form, style="TFrame")
        btn_frame.grid(row=row, column=0, columnspan=2, pady=(12, 0), sticky="ew")

        tk.Button(
            btn_frame, text="Save", bg=Theme.SUCCESS, fg=Theme.WHITE,
            font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0,
            padx=16, pady=6, command=self._handle_submit,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_frame, text="Cancel", bg=Theme.DANGER, fg=Theme.WHITE,
            font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0,
            padx=16, pady=6, command=self.destroy,
        ).pack(side="left")

    def _handle_submit(self) -> None:
        """Validate and submit the prescription."""
        medicine = self._vars["medicine_name"].get().strip()
        if not medicine:
            messagebox.showwarning("Warning", "Medicine name is required.", parent=self)
            return

        data = {key: var.get().strip() for key, var in self._vars.items()}
        data["instructions"] = self._instructions_text.get("1.0", tk.END).strip()
        self._on_submit(data)
        self.destroy()


# ── Visit Detail View ──────────────────────────────────────────

class VisitDetailView(BaseView):
    """Detailed view of a single visit with tabs for information,
    prescriptions, and test reports.
    """

    def __init__(
        self,
        parent: tk.Widget,
        visit_id: int,
        visit_data: Dict[str, Any],
        on_back: Optional[Callable] = None,
        on_add_prescription: Optional[Callable[[int], None]] = None,
        on_delete_prescription: Optional[Callable[[int], None]] = None,
        on_upload_report: Optional[Callable[[int, str], None]] = None,
        on_download_report: Optional[Callable[[int], None]] = None,
        on_delete_report: Optional[Callable[[int], None]] = None,
        on_upload_document: Optional[Callable[[str], None]] = None,
        on_download_document: Optional[Callable[[int, str], None]] = None,
        on_delete_document: Optional[Callable[[int], None]] = None,
        **kwargs,
    ) -> None:
        """Initialise the visit detail view.

        Args:
            parent: Parent tkinter widget.
            visit_id: The visit record ID.
            visit_data: Full visit record dict with prescriptions, reports
                and (optionally) documents for the visit's patient.
            on_back: Callback to return to previous view.
            on_add_prescription: Callback when adding a prescription.
            on_delete_prescription: Callback when deleting a prescription.
            on_upload_report: Callback(visit_id, doc_type) when uploading a report.
            on_download_report: Callback when downloading a report.
            on_delete_report: Callback when deleting a report.
            on_upload_document: Callback(patient_id) when uploading a document.
            on_download_document: Callback when downloading a document.
            on_delete_document: Callback when deleting a document.
        """
        super().__init__(parent, **kwargs)
        self._visit_id = visit_id
        self._visit_data = visit_data
        self._on_back = on_back
        self._on_add_prescription = on_add_prescription
        self._on_delete_prescription = on_delete_prescription
        self._on_upload_report = on_upload_report
        self._on_download_report = on_download_report
        self._on_delete_report = on_delete_report
        self._on_upload_document = on_upload_document
        self._on_download_document = on_download_document
        self._on_delete_document = on_delete_document
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the visit detail layout."""
        # ── Header ─────────────────────────────────────────────
        header = ttk.Frame(self, style="Header.TFrame", padding=16)
        header.pack(fill="x")

        if self._on_back:
            tk.Button(
                header, text="← Back", bg=Theme.LIGHT, fg=Theme.DARK_TEXT,
                font=Theme.FONT_SMALL_BOLD, cursor="hand2", bd=0,
                padx=10, pady=2, command=self._on_back,
            ).pack(side="left", padx=(0, 16))

        ttk.Label(
            header, text=f"Visit #{self._visit_id}",
            style="Heading.TLabel",
        ).pack(side="left")

        # ── Visit info card ────────────────────────────────────
        info_frame = ttk.Frame(self, style="TFrame", padding=16)
        info_frame.pack(fill="x")

        card = ttk.Frame(info_frame, style="Card.TFrame", padding=16)
        card.pack(fill="x")

        visit_date = self._visit_data.get("visit_date", "")
        if hasattr(visit_date, "strftime"):
            visit_date = visit_date.strftime("%Y-%m-%d")

        fields = [
            ("Patient", self._visit_data.get("patient_name", self._visit_data.get("patient_id", ""))),
            ("Doctor", self._visit_data.get("doctor_name", "")),
            ("Date", visit_date),
            ("Status", self._visit_data.get("status", "")),
        ]
        for idx, (label, value) in enumerate(fields):
            ttk.Label(card, text=f"{label}:", style="Card.TLabel").grid(
                row=idx, column=0, sticky="w", padx=(0, 8), pady=2,
            )
            ttk.Label(card, text=str(value), style="Subheading.TLabel").grid(
                row=idx, column=1, sticky="w", pady=2,
            )

        # Diagnosis
        diagnosis = self._visit_data.get("diagnosis", "")
        if diagnosis:
            ttk.Label(card, text="Diagnosis:", style="Card.TLabel").grid(
                row=len(fields), column=0, sticky="nw", padx=(0, 8), pady=(8, 2),
            )
            ttk.Label(card, text=diagnosis, style="Card.TLabel", wraplength=500).grid(
                row=len(fields), column=1, sticky="w", pady=(8, 2),
            )

        # Doctor notes
        notes = self._visit_data.get("doctor_notes", "")
        if notes:
            notes_row = len(fields) + (1 if diagnosis else 0)
            ttk.Label(card, text="Notes:", style="Card.TLabel").grid(
                row=notes_row, column=0, sticky="nw", padx=(0, 8), pady=(8, 2),
            )
            notes_text = tk.Text(card, height=3, width=60, font=Theme.FONT_BODY, wrap="word", bg=Theme.SURFACE, fg=Theme.DARK_TEXT, insertbackground=Theme.DARK_TEXT, relief="flat")
            notes_text.grid(row=notes_row, column=1, sticky="ew", pady=(8, 2))
            notes_text.insert("1.0", notes)
            notes_text.configure(state="disabled")

        # ── Notebook for prescriptions and reports ────────────
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=16, pady=8)

        self._prescriptions_tab = ttk.Frame(notebook, style="TFrame")
        notebook.add(self._prescriptions_tab, text="Prescriptions")
        self._build_prescriptions_tab()

        self._reports_tab = ttk.Frame(notebook, style="TFrame")
        notebook.add(self._reports_tab, text="Test Reports")
        self._build_reports_tab()

        self._documents_tab = ttk.Frame(notebook, style="TFrame")
        notebook.add(self._documents_tab, text="Documents")
        self._build_documents_tab()

    def _build_prescriptions_tab(self) -> None:
        """Build the prescriptions tab content."""
        tab = self._prescriptions_tab
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=1)

        columns = ("id", "medicine", "dosage", "frequency", "duration", "instructions")
        self._rx_tree = self.create_treeview(
            tab, columns=columns,
            headings=("ID", "Medicine", "Dosage", "Frequency", "Duration", "Instructions"),
            height=10,
        )
        self._rx_tree.column("id", width=40, anchor="center")
        self._rx_tree.column("medicine", width=150)
        self._rx_tree.column("dosage", width=100)
        self._rx_tree.column("frequency", width=120)
        self._rx_tree.column("duration", width=80)
        self._rx_tree.column("instructions", width=200)

        # Populate prescriptions
        for rx in self._visit_data.get("prescriptions", []):
            self._rx_tree.insert("", "end", values=(
                rx.get("prescription_id", ""),
                rx.get("medicine_name", ""),
                rx.get("dosage", ""),
                rx.get("frequency", ""),
                rx.get("duration", ""),
                rx.get("instructions", ""),
            ), iid=str(rx.get("prescription_id", "")))
        self.apply_default_sort(self._rx_tree)

        # Action buttons
        btn_frame = ttk.Frame(tab, style="TFrame")
        btn_frame.grid(row=1, column=0, columnspan=2, pady=8, sticky="ew")

        if self._on_add_prescription:
            tk.Button(
                btn_frame, text="+ Add Prescription", bg=Theme.SUCCESS, fg=Theme.WHITE,
                font=Theme.FONT_SMALL_BOLD, cursor="hand2", bd=0,
                padx=10, pady=4,
                command=lambda: self._on_add_prescription(self._visit_id),
            ).pack(side="left", padx=(0, 8))

        if self._on_delete_prescription:
            tk.Button(
                btn_frame, text="Delete", bg=Theme.DANGER, fg=Theme.WHITE,
                font=Theme.FONT_SMALL_BOLD, cursor="hand2", bd=0,
                padx=10, pady=4, command=self._handle_delete_rx,
            ).pack(side="left")

    def _build_reports_tab(self) -> None:
        """Build the test reports tab content."""
        tab = self._reports_tab
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=1)

        columns = ("id", "name", "type", "size", "date")
        self._report_tree = self.create_treeview(
            tab, columns=columns,
            headings=("ID", "File Name", "Type", "Size", "Upload Date"),
            height=10,
        )
        self._report_tree.column("id", width=40, anchor="center")
        self._report_tree.column("name", width=200)
        self._report_tree.column("type", width=80, anchor="center")
        self._report_tree.column("size", width=80, anchor="center")
        self._report_tree.column("date", width=120, anchor="center")

        # Populate reports
        for r in self._visit_data.get("reports", []):
            upload_date = r.get("upload_date", "")
            if hasattr(upload_date, "strftime"):
                upload_date = upload_date.strftime("%Y-%m-%d %H:%M")

            size = r.get("file_size", 0)
            if size:
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
            else:
                size_str = ""

            self._report_tree.insert("", "end", values=(
                r.get("report_id", ""),
                r.get("report_name", ""),
                r.get("file_type", ""),
                size_str,
                upload_date,
            ), iid=str(r.get("report_id", "")))
        self.apply_default_sort(self._report_tree)

        # ── Upload controls (type selector + button) ──────────
        upload_frame = ttk.Frame(tab, style="TFrame")
        upload_frame.grid(row=1, column=0, columnspan=2, pady=(8, 0), sticky="ew")

        ttk.Label(upload_frame, text="Type:", font=Theme.FONT_BODY).pack(
            side="left", padx=(0, 6),
        )
        self._report_type_var = tk.StringVar()
        self._report_type_combo = ttk.Combobox(
            upload_frame, textvariable=self._report_type_var,
            values=ReportType.ALL, width=14, state="readonly",
            font=Theme.FONT_BODY,
        )
        self._report_type_combo.pack(side="left", padx=(0, 8))

        if self._on_upload_report:
            tk.Button(
                upload_frame, text="Upload Report", bg=Theme.ACCENT, fg=Theme.WHITE,
                font=Theme.FONT_SMALL_BOLD, cursor="hand2", bd=0,
                padx=10, pady=4, command=self._handle_upload_report,
            ).pack(side="left")

        ttk.Label(
            upload_frame, text="Select a type, then choose a .pdf / .jpg / .jpeg / .png / .dcm file",
            style="TLabel",
        ).pack(side="left", padx=(12, 0))

        # ── Action buttons ─────────────────────────────────────
        action_frame = ttk.Frame(tab, style="TFrame")
        action_frame.grid(row=2, column=0, columnspan=2, pady=8, sticky="ew")

        if self._on_download_report:
            tk.Button(
                action_frame, text="Download", bg=Theme.SUCCESS, fg=Theme.WHITE,
                font=Theme.FONT_SMALL_BOLD, cursor="hand2", bd=0,
                padx=10, pady=4, command=self._handle_download_report,
            ).pack(side="left", padx=(0, 8))

        if self._on_delete_report:
            tk.Button(
                action_frame, text="Delete", bg=Theme.DANGER, fg=Theme.WHITE,
                font=Theme.FONT_SMALL_BOLD, cursor="hand2", bd=0,
                padx=10, pady=4, command=self._handle_delete_report,
            ).pack(side="left")

    def _build_documents_tab(self) -> None:
        """Build the patient documents tab content.

        Patient-level documents (consent forms, referrals, scans) are
        listed here and attach to the visit's patient.  The file picker
        restricts selectable types to the supported extensions as a
        first line of UX guidance — authoritative validation (extension
        allow-list, magic bytes, size cap) happens backend-side in
        ``DocumentService``.
        """
        tab = self._documents_tab
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=1)

        columns = ("id", "name", "type", "size", "date")
        self._document_tree = self.create_treeview(
            tab, columns=columns,
            headings=("ID", "File Name", "Type", "Size", "Upload Date"),
            height=10,
        )
        self._document_tree.column("id", width=40, anchor="center")
        self._document_tree.column("name", width=200)
        self._document_tree.column("type", width=80, anchor="center")
        self._document_tree.column("size", width=80, anchor="center")
        self._document_tree.column("date", width=120, anchor="center")

        # Populate documents
        for doc in self._visit_data.get("documents", []):
            self._insert_document(doc)
        self.apply_default_sort(self._document_tree)

        # ── Upload button ───────────────────────────────────────
        upload_frame = ttk.Frame(tab, style="TFrame")
        upload_frame.grid(row=1, column=0, columnspan=2, pady=(8, 0), sticky="ew")

        if self._on_upload_document:
            tk.Button(
                upload_frame, text="Upload Document", bg=Theme.ACCENT, fg=Theme.WHITE,
                font=Theme.FONT_SMALL_BOLD, cursor="hand2", bd=0,
                padx=10, pady=4, command=self._handle_upload_document,
            ).pack(side="left")

        ttk.Label(
            upload_frame,
            text="Allowed types: .pdf / .jpg / .jpeg / .png / .dcm (max 10 MB)",
            style="TLabel",
        ).pack(side="left", padx=(12, 0))

        # ── Action buttons ─────────────────────────────────────
        action_frame = ttk.Frame(tab, style="TFrame")
        action_frame.grid(row=2, column=0, columnspan=2, pady=8, sticky="ew")

        if self._on_download_document:
            tk.Button(
                action_frame, text="Download", bg=Theme.SUCCESS, fg=Theme.WHITE,
                font=Theme.FONT_SMALL_BOLD, cursor="hand2", bd=0,
                padx=10, pady=4, command=self._handle_download_document,
            ).pack(side="left", padx=(0, 8))

        if self._on_delete_document:
            tk.Button(
                action_frame, text="Delete", bg=Theme.DANGER, fg=Theme.WHITE,
                font=Theme.FONT_SMALL_BOLD, cursor="hand2", bd=0,
                padx=10, pady=4, command=self._handle_delete_document,
            ).pack(side="left")

    def _insert_document(self, doc: Dict[str, Any]) -> None:
        """Insert a single document row into the tree.

        Args:
            doc: Document record dict.
        """
        upload_date = doc.get("upload_date", "")
        if hasattr(upload_date, "strftime"):
            upload_date = upload_date.strftime("%Y-%m-%d %H:%M")

        size = doc.get("file_size", 0)
        if size:
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"
        else:
            size_str = ""

        self._document_tree.insert("", "end", values=(
            doc.get("document_id", ""),
            doc.get("document_name", ""),
            doc.get("file_type", ""),
            size_str,
            upload_date,
        ), iid=str(doc.get("document_id", "")))

    # ── Internal handlers ──────────────────────────────────────

    def _handle_upload_report(self) -> None:
        """Validate the selected report type and trigger the upload."""
        doc_type = self._report_type_var.get().strip()
        if not doc_type:
            messagebox.showwarning(
                "Warning", "Please select a report type before uploading.", parent=self,
            )
            return
        self._on_upload_report(self._visit_id, doc_type)

    def _handle_delete_rx(self) -> None:
        """Delete the selected prescription."""
        selection = self._rx_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a prescription.", parent=self)
            return
        rx_id = int(selection[0])
        if messagebox.askyesno("Confirm", "Delete this prescription?", parent=self):
            self._on_delete_prescription(rx_id)

    def _handle_download_report(self) -> None:
        """Download the selected report."""
        selection = self._report_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a report.", parent=self)
            return
        report_id = int(selection[0])
        dest = filedialog.askdirectory(title="Select Download Destination")
        if dest:
            self._on_download_report(report_id, dest)

    def _handle_delete_report(self) -> None:
        """Delete the selected report."""
        selection = self._report_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a report.", parent=self)
            return
        report_id = int(selection[0])
        if messagebox.askyesno("Confirm", "Delete this test report?", parent=self):
            self._on_delete_report(report_id)

    def _handle_upload_document(self) -> None:
        """Trigger a document upload for the visit's patient."""
        patient_id = self._visit_data.get("patient_id", "")
        if not patient_id:
            messagebox.showwarning(
                "Warning", "No patient is associated with this visit.", parent=self,
            )
            return
        self._on_upload_document(patient_id)

    def _handle_download_document(self) -> None:
        """Download the selected document."""
        selection = self._document_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a document.", parent=self)
            return
        document_id = int(selection[0])
        dest = filedialog.askdirectory(title="Select Download Destination")
        if dest:
            self._on_download_document(document_id, dest)

    def _handle_delete_document(self) -> None:
        """Delete the selected document."""
        selection = self._document_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a document.", parent=self)
            return
        document_id = int(selection[0])
        if messagebox.askyesno("Confirm", "Delete this document?", parent=self):
            self._on_delete_document(document_id)

    def update_prescriptions(self, prescriptions: List[Dict[str, Any]]) -> None:
        """Refresh the prescriptions list.

        Args:
            prescriptions: Updated list of prescription dicts.
        """
        self._rx_tree.delete(*self._rx_tree.get_children())
        for rx in prescriptions:
            self._rx_tree.insert("", "end", values=(
                rx.get("prescription_id", ""),
                rx.get("medicine_name", ""),
                rx.get("dosage", ""),
                rx.get("frequency", ""),
                rx.get("duration", ""),
                rx.get("instructions", ""),
            ), iid=str(rx.get("prescription_id", "")))
        self.apply_default_sort(self._rx_tree)

    def update_reports(self, reports: List[Dict[str, Any]]) -> None:
        """Refresh the reports list.

        Args:
            reports: Updated list of report dicts.
        """
        self._report_tree.delete(*self._report_tree.get_children())
        for r in reports:
            upload_date = r.get("upload_date", "")
            if hasattr(upload_date, "strftime"):
                upload_date = upload_date.strftime("%Y-%m-%d %H:%M")

            size = r.get("file_size", 0)
            if size:
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
            else:
                size_str = ""

            self._report_tree.insert("", "end", values=(
                r.get("report_id", ""),
                r.get("report_name", ""),
                r.get("file_type", ""),
                size_str,
                upload_date,
            ), iid=str(r.get("report_id", "")))
        self.apply_default_sort(self._report_tree)

    def update_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Refresh the documents list.

        Args:
            documents: Updated list of document dicts.
        """
        self._document_tree.delete(*self._document_tree.get_children())
        for doc in documents:
            self._insert_document(doc)
        self.apply_default_sort(self._document_tree)


# ── Patient Timeline View ──────────────────────────────────────

class PatientTimelineView(BaseView):
    """Full-screen timeline view for a single patient's clinical history."""

    def __init__(
        self,
        parent: tk.Widget,
        patient_id: str,
        patient_name: str,
        visits: List[Dict[str, Any]],
        on_back: Optional[Callable] = None,
        on_create_visit: Optional[Callable[[str], None]] = None,
        on_view_visit: Optional[Callable[[int], None]] = None,
        **kwargs,
    ) -> None:
        """Initialise the patient timeline view.

        Args:
            parent: Parent tkinter widget.
            patient_id: The patient ID.
            patient_name: The patient's name.
            visits: List of visit records with prescriptions and reports.
            on_back: Callback to return to previous view.
            on_create_visit: Callback when creating a new visit.
            on_view_visit: Callback when viewing a visit detail.
        """
        super().__init__(parent, **kwargs)
        self._patient_id = patient_id
        self._patient_name = patient_name
        self._visits = visits
        self._on_back = on_back
        self._on_create_visit = on_create_visit
        self._on_view_visit = on_view_visit
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the timeline layout."""
        # ── Header ─────────────────────────────────────────────
        header = ttk.Frame(self, style="Header.TFrame", padding=16)
        header.pack(fill="x")

        if self._on_back:
            tk.Button(
                header, text="← Back", bg=Theme.LIGHT, fg=Theme.DARK_TEXT,
                font=Theme.FONT_SMALL_BOLD, cursor="hand2", bd=0,
                padx=10, pady=2, command=self._on_back,
            ).pack(side="left", padx=(0, 16))

        ttk.Label(
            header, text=f"Patient Timeline: {self._patient_id} - {self._patient_name}",
            style="Heading.TLabel",
        ).pack(side="left")

        if self._on_create_visit:
            tk.Button(
                header, text="+ New Visit", bg=Theme.SUCCESS, fg=Theme.WHITE,
                font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0,
                padx=12, pady=4,
                command=lambda: self._on_create_visit(self._patient_id),
            ).pack(side="right")

        # ── Stats summary ──────────────────────────────────────
        stats_frame = ttk.Frame(self, style="TFrame", padding=(16, 8))
        stats_frame.pack(fill="x")

        total_visits = len(self._visits)
        total_rx = sum(len(v.get("prescriptions", [])) for v in self._visits)
        total_reports = sum(len(v.get("reports", [])) for v in self._visits)

        ttk.Label(
            stats_frame,
            text=f"Visits: {total_visits}  |  Prescriptions: {total_rx}  |  Reports: {total_reports}",
            style="Subheading.TLabel",
        ).pack(anchor="w")

        # ── Timeline ───────────────────────────────────────────
        timeline_frame = ttk.Frame(self, style="TFrame", padding=16)
        timeline_frame.pack(fill="both", expand=True)
        timeline_frame.columnconfigure(0, weight=1)
        timeline_frame.rowconfigure(0, weight=1)

        if not self._visits:
            ttk.Label(
                timeline_frame, text="No visit records found.",
                style="TLabel",
            ).grid(row=0, column=0, pady=40)
            return

        canvas = tk.Canvas(timeline_frame, bg=Theme.BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(timeline_frame, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas, style="TFrame")
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        timeline_frame.rowconfigure(0, weight=1)

        for visit in self._visits:
            self._create_visit_card(scroll_frame, visit)

    def _create_visit_card(self, parent: ttk.Frame, visit: Dict[str, Any]) -> None:
        """Create a detailed visit card with prescriptions and reports.

        Args:
            parent: Parent frame.
            visit: Visit record dict.
        """
        card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        card.pack(fill="x", pady=(0, 12))

        visit_date = visit.get("visit_date", "")
        if hasattr(visit_date, "strftime"):
            visit_date = visit_date.strftime("%b %d, %Y")

        # Header row
        header_row = ttk.Frame(card, style="Card.TFrame")
        header_row.pack(fill="x")

        ttk.Label(
            header_row, text=f"Visit #{visit.get('visit_id', '')} — {visit_date}",
            style="Subheading.TLabel",
        ).pack(side="left")

        visit_id = visit.get("visit_id", 0)
        tk.Button(
            header_row, text="View Full Details", bg=Theme.ACCENT, fg=Theme.WHITE,
            font=Theme.FONT_SMALL_BOLD, cursor="hand2", bd=0,
            padx=8, pady=2,
            command=lambda vid=visit_id: self._on_view_visit(vid),
        ).pack(side="right")

        # Diagnosis
        diagnosis = visit.get("diagnosis", "")
        if diagnosis:
            ttk.Label(card, text=f"Diagnosis: {diagnosis}", style="Card.TLabel",
                      wraplength=600).pack(anchor="w", pady=(4, 0))

        # Doctor notes (truncated)
        notes = visit.get("doctor_notes", "")
        if notes:
            ttk.Label(card, text=f"Notes: {notes[:150]}{'...' if len(notes) > 150 else ''}",
                      style="Card.TLabel", wraplength=600).pack(anchor="w")

        # Prescriptions
        prescriptions = visit.get("prescriptions", [])
        if prescriptions:
            rx_frame = ttk.Frame(card, style="Card.TFrame")
            rx_frame.pack(fill="x", pady=(4, 0))
            ttk.Label(rx_frame, text="Prescriptions:", style="Card.TLabel",
                      font=Theme.FONT_SMALL_BOLD).pack(anchor="w")
            for rx in prescriptions:
                parts = [
                    rx.get("medicine_name", ""),
                    rx.get("dosage", ""),
                    rx.get("frequency", ""),
                ]
                rx_text = " — ".join(p for p in parts if p)
                ttk.Label(rx_frame, text=f"  • {rx_text}",
                          style="Card.TLabel", font=Theme.FONT_SMALL).pack(anchor="w")

        # Test reports
        reports = visit.get("reports", [])
        if reports:
            rpt_frame = ttk.Frame(card, style="Card.TFrame")
            rpt_frame.pack(fill="x", pady=(4, 0))
            ttk.Label(rpt_frame, text="Test Reports:", style="Card.TLabel",
                      font=Theme.FONT_SMALL_BOLD).pack(anchor="w")
            for r in reports:
                ttk.Label(rpt_frame, text=f"  • {r.get('report_name', '')} ({r.get('file_type', '')})",
                          style="Card.TLabel", font=Theme.FONT_SMALL).pack(anchor="w")
