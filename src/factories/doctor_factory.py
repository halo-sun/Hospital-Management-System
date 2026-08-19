"""Doctor view factory – configures navigation and views for the Doctor role.

Extracted from ``src.app.Application`` to isolate the doctor
role-setup logic.
"""
from __future__ import annotations

import logging
import os
from typing import (
    Any, Dict,
)

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from src.controllers.auth_controller import AuthController
from src.controllers.doctor_controller import DoctorController
from src.controllers.appointment_controller import AppointmentController
from src.controllers.clinical_controller import ClinicalController
from src.controllers.document_controller import DocumentController
from src.controllers.patient_controller import PatientController
from src.gui.main_window import MainWindow
from src.gui.doctor.dashboard_view import DoctorDashboard
from src.gui.receptionist.appointment_views import AppointmentListView
from src.gui.doctor.clinical_views import (
    ClinicalRecordsView,
    VisitFormView,
    VisitDetailView,
    PrescriptionFormDialog,
    PatientTimelineView,
)

logger = logging.getLogger(__name__)


class DoctorViewFactory:
    """Creates and registers all doctor-specific views."""

    def __init__(
        self,
        main_window: MainWindow,
        auth_ctrl: AuthController,
        doctor_ctrl: DoctorController,
        patient_ctrl: PatientController,
        appt_ctrl: AppointmentController,
        clinical_ctrl: ClinicalController,
        document_ctrl: Optional[DocumentController] = None,
    ) -> None:
        """Initialise the factory with shared dependencies.

        Args:
            main_window: The application's main window.
            auth_ctrl: Authentication/authorisation controller.
            doctor_ctrl: Doctor management controller.
            appt_ctrl: Appointment management controller.
            clinical_ctrl: Clinical records controller.
            document_ctrl: Patient document controller (defaults to a
                new instance if not supplied).
        """
        self._main_window = main_window
        self._auth_ctrl = auth_ctrl
        self._doctor_ctrl = doctor_ctrl
        self._patient_ctrl = patient_ctrl
        self._appt_ctrl = appt_ctrl
        self._clinical_ctrl = clinical_ctrl
        self._document_ctrl = document_ctrl or DocumentController(auth_ctrl)

    def setup(self, user: Dict[str, Any]) -> None:
        """Register sidebar items and view factories for the doctor.

        Args:
            user: The authenticated user dictionary.
        """
        doctor = self._doctor_ctrl.get_doctor_by_user_id(user["user_id"])
        self._doctor_id = doctor.get("doctor_id", 0) if doctor else 0
        doctor_name = doctor.get("full_name", "") if doctor else user.get("full_name", "")
        today_appts = self._appt_ctrl.get_doctor_appointments(
            self._doctor_id,
        )

        self._main_window.set_sidebar_items([
            ("dashboard", "Dashboard"),
            ("today_appointments", "Today's Appointments"),
            ("my_schedule", "My Schedule"),
            ("clinical_records", "Clinical Records"),
        ])

        self._main_window.register_view(
            "dashboard",
            lambda p: DoctorDashboard(p, doctor_name, today_appts, self._main_window.navigate_to),
        )
        self._main_window.register_view(
            "today_appointments",
            lambda p: AppointmentListView(
                p, today_appts,
                on_refresh=lambda: self._main_window.navigate_to("today_appointments", force=True),
            ),
        )
        self._main_window.register_view(
            "my_schedule",
            lambda p: self._create_schedule_view(p),
        )
        self._main_window.register_view(
            "clinical_records",
            lambda p: self._create_clinical_records_view(p),
        )

        self._main_window.navigate_to("dashboard")

    # ── Clinical Records ───────────────────────────────────────

    def _create_clinical_records_view(self, parent: tk.Widget) -> tk.Widget:
        """Create the main clinical records view.

        Args:
            parent: Parent tkinter widget.

        Returns:
            The ClinicalRecordsView widget.
        """
        return ClinicalRecordsView(
            parent,
            doctor_id=self._doctor_id,
            on_search=self._handle_clinical_search,
            on_patient_selected=self._handle_patient_selected,
            on_create_visit=self._handle_create_visit,
            on_view_visit=self._handle_view_visit,
        )

    def _handle_clinical_search(
        self, search_term: str,
    ) -> None:
        """Search for patients in the doctor's visit records.

        Args:
            search_term: Patient name or ID term.
        """
        visits = self._clinical_ctrl.search_patient_visits(
            self._doctor_id, search_term,
        )

        # Group by patient
        patient_map: Dict[str, Dict[str, Any]] = {}
        for v in visits:
            pid = v.get("patient_id", "")
            if pid not in patient_map:
                patient_map[pid] = {
                    "patient_id": pid,
                    "patient_name": v.get("patient_name", ""),
                    "count": 0,
                }
            patient_map[pid]["count"] += 1

        patients = list(patient_map.values())
        current_view = self._main_window.get_current_content()
        if isinstance(current_view, ClinicalRecordsView):
            current_view.set_patients(patients)

    def _handle_patient_selected(self, patient_id: str) -> None:
        """Show the timeline for the selected patient.

        Args:
            patient_id: The patient ID.
        """
        timeline = self._clinical_ctrl.get_patient_timeline(patient_id)

        view = PatientTimelineView(
            parent=self._main_window.get_content_parent(),
            patient_id=patient_id,
            patient_name=timeline[0].get("patient_name", "") if timeline else "",
            visits=timeline,
            on_back=lambda: self._main_window.navigate_to("clinical_records"),
            on_create_visit=self._handle_create_visit,
            on_view_visit=self._handle_view_visit,
        )
        self._main_window.show_content(view)

    def _handle_create_visit(self, patient_id: str) -> None:
        """Open the visit creation form.

        Args:
            patient_id: The patient ID.
        """
        patient = self._patient_ctrl.get_patient(patient_id)
        patient_name = patient.get("full_name", patient_id) if patient else patient_id

        view = VisitFormView(
            parent=self._main_window.get_content_parent(),
            patient_id=patient_id,
            patient_name=patient_name,
            doctor_id=self._doctor_id,
            on_submit=lambda data: self._handle_visit_submit(data, patient_id),
            on_cancel=lambda: self._main_window.navigate_to("clinical_records"),
        )
        self._main_window.show_content(view)

    def _handle_visit_submit(
        self, data: Dict[str, Any], patient_id: str,
    ) -> None:
        """Save a new visit record.

        Args:
            data: Visit form data.
            patient_id: The patient ID.
        """
        # Get the appointment for this patient and doctor today
        from src.constants import AppointmentStatus
        from datetime import date

        today = date.today()
        appointments = self._appt_ctrl.get_doctor_appointments(self._doctor_id, today)
        appointment_id = None
        for appt in appointments:
            if appt.get("patient_id") == patient_id and appt.get("status") == AppointmentStatus.COMPLETED:
                appointment_id = appt.get("appointment_id")
                break
            elif appt.get("patient_id") == patient_id:
                appointment_id = appt.get("appointment_id")
                # Don't break — prefer completed appointment

        if not appointment_id:
            # Use today's appointments as fallback
            if appointments:
                appointment_id = appointments[0].get("appointment_id")

        visit_data = {
            "appointment_id": data.get("appointment_id") or appointment_id or 0,
            "doctor_id": self._doctor_id,
            "visit_date": data.get("visit_date", str(today)),
            "symptoms": data.get("symptoms", ""),
            "diagnosis": data.get("diagnosis", ""),
            "doctor_notes": data.get("doctor_notes", ""),
            "follow_up_date": data.get("follow_up_date", None) or None,
        }

        user_id = self._auth_ctrl.get_current_user_id() if hasattr(self._auth_ctrl, "get_current_user_id") else None
        success, message, visit_id = self._clinical_ctrl.create_visit(
            visit_data, user_id=user_id,
        )

        if success:
            messagebox.showinfo("Success", message)
            # Navigate back to clinical records or view the visit
            self._main_window.navigate_to("clinical_records")
        else:
            messagebox.showerror("Error", message)

    def _handle_view_visit(self, visit_id: int) -> None:
        """Show the visit detail view.

        Args:
            visit_id: The visit record ID.
        """
        visit_data = self._clinical_ctrl.get_visit(visit_id)
        if not visit_data:
            messagebox.showerror("Error", "Visit record not found.")
            return

        # Attach the patient's documents so the Documents tab renders
        # without a second round-trip.
        patient_id = visit_data.get("patient_id", "")
        if patient_id:
            visit_data["documents"] = self._document_ctrl.list_documents(patient_id)

        view = VisitDetailView(
            parent=self._main_window.get_content_parent(),
            visit_id=visit_id,
            visit_data=visit_data,
            on_back=lambda: self._main_window.navigate_to("clinical_records"),
            on_add_prescription=self._handle_add_prescription,
            on_delete_prescription=self._handle_delete_prescription,
            on_upload_report=self._handle_upload_report,
            on_download_report=self._handle_download_report,
            on_delete_report=self._handle_delete_report,
            on_upload_document=self._handle_upload_document,
            on_download_document=self._handle_download_document,
            on_delete_document=self._handle_delete_document,
        )
        self._main_window.show_content(view)

    # ── Prescription handlers ──────────────────────────────────

    def _handle_add_prescription(self, visit_id: int) -> None:
        """Open the prescription dialog for a visit.

        Args:
            visit_id: The visit record ID.
        """
        dialog = PrescriptionFormDialog(
            self._main_window.get_content_parent(),
            on_submit=lambda data: self._handle_prescription_submit(visit_id, data),
        )

    def _handle_prescription_submit(
        self, visit_id: int, data: Dict[str, str],
    ) -> None:
        """Save a new prescription and update the visit detail view.

        Args:
            visit_id: The visit record ID.
            data: Prescription form data.
        """
        user_id = self._auth_ctrl.get_current_user_id() if hasattr(self._auth_ctrl, "get_current_user_id") else None
        success, message, rx_id = self._clinical_ctrl.add_prescription(
            visit_id, data, user_id=user_id,
        )

        if success:
            # Refresh the visit detail view
            self._handle_view_visit(visit_id)
        else:
            messagebox.showerror("Error", message)

    def _handle_delete_prescription(self, prescription_id: int) -> None:
        """Delete a prescription and refresh the view.

        Args:
            prescription_id: The prescription ID.
        """
        user_id = self._auth_ctrl.get_current_user_id() if hasattr(self._auth_ctrl, "get_current_user_id") else None
        success, message = self._clinical_ctrl.delete_prescription(
            prescription_id, user_id=user_id,
        )
        if not success:
            messagebox.showerror("Error", message)

    # ── Report handlers ────────────────────────────────────────

    def _handle_upload_report(self, visit_id: int, doc_type: str) -> None:
        """Open file dialog and upload a test report.

        The file picker restricts the selectable extensions to the
        supported document types as a first line of UX guidance — the
        authoritative extension/magic-byte validation is a backend
        concern (Backend Phase C).

        Args:
            visit_id: The visit record ID.
            doc_type: Report category (see ``ReportType``).
        """
        file_path = filedialog.askopenfilename(
            title="Select Test Report File",
            filetypes=[
                ("PDF Documents", "*.pdf"),
                ("Images", "*.jpg *.jpeg *.png"),
                ("DICOM", "*.dcm"),
            ],
        )
        if not file_path:
            return

        user_id = self._auth_ctrl.get_current_user_id() if hasattr(self._auth_ctrl, "get_current_user_id") else None
        success, message, report_id = self._clinical_ctrl.upload_report(
            visit_id, file_path, doc_type=doc_type, user_id=user_id,
        )

        if success:
            messagebox.showinfo(
                "Success", message, parent=self._main_window.get_content_parent(),
            )
            # Refresh the visit detail view
            self._handle_view_visit(visit_id)
        else:
            messagebox.showerror("Error", message, parent=self._main_window.get_content_parent())

    def _handle_download_report(self, report_id: int, dest_dir: str) -> None:
        """Download a test report to the chosen directory.

        Args:
            report_id: The report ID.
            dest_dir: Destination directory path.
        """
        success, message = self._clinical_ctrl.download_report(report_id, dest_dir)
        if success:
            messagebox.showinfo("Success", message)
        else:
            messagebox.showerror("Error", message)

    def _handle_delete_report(self, report_id: int) -> None:
        """Delete a test report and refresh the view.

        Args:
            report_id: The report ID.
        """
        user_id = self._auth_ctrl.get_current_user_id() if hasattr(self._auth_ctrl, "get_current_user_id") else None
        success, message = self._clinical_ctrl.delete_report(
            report_id, user_id=user_id,
        )
        if not success:
            messagebox.showerror("Error", message)

    # ── Patient document handlers ──────────────────────────────

    def _handle_upload_document(self, patient_id: str) -> None:
        """Open the file dialog and upload a patient document.

        The file picker restricts selectable extensions to the
        supported types as first-line UX guidance — the authoritative
        extension/magic-byte/size validation is enforced by
        ``DocumentService``.

        Args:
            patient_id: The patient the document belongs to.
        """
        file_path = filedialog.askopenfilename(
            title="Select Document File",
            filetypes=[
                ("PDF Documents", "*.pdf"),
                ("Images", "*.jpg *.jpeg *.png"),
                ("DICOM", "*.dcm"),
            ],
        )
        if not file_path:
            return

        user_id = self._auth_ctrl.get_current_user_id() if hasattr(self._auth_ctrl, "get_current_user_id") else None
        success, message, document_id = self._document_ctrl.upload_document(
            patient_id, file_path, user_id=user_id,
        )

        if success:
            messagebox.showinfo(
                "Success", message, parent=self._main_window.get_content_parent(),
            )
            # Refresh the documents list in the open visit detail view.
            current_view = self._main_window.get_current_content()
            if current_view is not None and hasattr(current_view, "update_documents"):
                current_view.update_documents(
                    self._document_ctrl.list_documents(patient_id),
                )
        else:
            messagebox.showerror("Error", message, parent=self._main_window.get_content_parent())

    def _handle_download_document(self, document_id: int, dest_dir: str) -> None:
        """Download a document to the chosen directory.

        Args:
            document_id: The document ID.
            dest_dir: Destination directory path.
        """
        doc = self._document_ctrl.get_document(document_id)
        if not doc:
            messagebox.showerror("Error", "Document not found.")
            return

        src_path = doc.get("file_path", "")
        if not src_path or not os.path.isfile(src_path):
            messagebox.showerror("Error", "Document file not found on disk.")
            return

        import shutil

        dest_path = os.path.join(dest_dir, doc.get("document_name", f"document_{document_id}"))
        try:
            shutil.copy2(src_path, dest_path)
            messagebox.showinfo("Success", f"Document saved to {dest_path}")
        except OSError as e:
            messagebox.showerror("Error", f"Failed to save file: {e}")

    def _handle_delete_document(self, document_id: int) -> None:
        """Delete a document and refresh the view.

        Args:
            document_id: The document ID.
        """
        user_id = self._auth_ctrl.get_current_user_id() if hasattr(self._auth_ctrl, "get_current_user_id") else None
        success, message = self._document_ctrl.delete_document(
            document_id, user_id=user_id,
        )
        if not success:
            messagebox.showerror("Error", message)
            return

        # Refresh the documents list in the open visit detail view.
        current_view = self._main_window.get_current_content()
        if current_view is not None and hasattr(current_view, "update_documents"):
            patient_id = getattr(current_view, "_visit_data", {}).get("patient_id", "")
            if patient_id:
                current_view.update_documents(
                    self._document_ctrl.list_documents(patient_id),
                )

    def _create_schedule_view(self, parent: tk.Widget) -> ttk.Frame:
        """Show the logged-in doctor's persisted weekly working schedule."""
        frame = ttk.Frame(parent, style="TFrame", padding=24)
        ttk.Label(frame, text="My Schedule", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(
            frame, text="Your configured weekly availability and lunch breaks.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 16))
        columns = ("day", "hours", "lunch", "availability", "slot")
        table = ttk.Treeview(frame, columns=columns, show="headings", height=8)
        for key, heading in zip(columns, ("Day", "Working Hours", "Lunch Break", "Available", "Slot (min)")):
            table.heading(key, text=heading)
            table.column(key, width=150, anchor="center")
        day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        for schedule in self._doctor_ctrl.get_doctor_schedule(self._doctor_id):
            start = str(schedule.get("start_time", ""))[:5]
            end = str(schedule.get("end_time", ""))[:5]
            lunch_start = str(schedule.get("lunch_break_start") or "")[:5]
            lunch_end = str(schedule.get("lunch_break_end") or "")[:5]
            lunch = f"{lunch_start} - {lunch_end}" if lunch_start and lunch_end else "None"
            day = day_names[int(schedule.get("day_of_week", 0))]
            table.insert("", "end", values=(day, f"{start} - {end}", lunch,
                                                "Yes" if schedule.get("is_available") else "No",
                                                schedule.get("slot_duration", "")))
        table.pack(fill="x")
        return frame
