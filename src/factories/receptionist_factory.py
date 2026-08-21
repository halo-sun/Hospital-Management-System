"""Receptionist view factory – configures navigation and views for the Receptionist role.

Extracted from ``src.app.Application`` to isolate the receptionist
role-setup logic.
"""
from __future__ import annotations

import logging
from typing import (
    Any, Dict, Tuple,
)

import tkinter as tk
from tkinter import messagebox

from src.controllers.auth_controller import AuthController
from src.controllers.patient_controller import PatientController
from src.controllers.doctor_controller import DoctorController
from src.controllers.appointment_controller import AppointmentController
from src.controllers.report_controller import ReportController
from src.gui.main_window import MainWindow
from src.gui.receptionist.dashboard_view import ReceptionistDashboard
from src.gui.receptionist.patient_views import PatientRegistrationView, PatientSearchView
from src.gui.receptionist.appointment_views import AppointmentBookingView, AppointmentListView
from src.gui.common.about_view import AboutView

logger = logging.getLogger(__name__)


class ReceptionistViewFactory:
    """Creates and registers all receptionist-specific views."""

    def __init__(
        self,
        main_window: MainWindow,
        auth_ctrl: AuthController,
        patient_ctrl: PatientController,
        doctor_ctrl: DoctorController,
        appt_ctrl: AppointmentController,
        report_ctrl: ReportController,
    ) -> None:
        """Initialise the factory with shared dependencies.

        Args:
            main_window: The application's main window.
            auth_ctrl: Authentication/authorisation controller.
            patient_ctrl: Patient management controller.
            doctor_ctrl: Doctor management controller.
            appt_ctrl: Appointment management controller.
            report_ctrl: Report/statistics controller.
        """
        self._main_window = main_window
        self._auth_ctrl = auth_ctrl
        self._patient_ctrl = patient_ctrl
        self._doctor_ctrl = doctor_ctrl
        self._appt_ctrl = appt_ctrl
        self._report_ctrl = report_ctrl

    def setup(self, user: Dict[str, Any]) -> None:
        """Register sidebar items and view factories for the receptionist.

        Args:
            user: The authenticated user dictionary.
        """
        stats = self._report_ctrl.get_dashboard_stats()

        self._main_window.set_sidebar_items([
            ("dashboard", "Dashboard"),
            ("register_patient", "Register Patient"),
            ("search_patient", "Search Patients"),
            ("book_appointment", "Book Appointment"),
            ("appointments", "Appointments"),
            ("about", "About"),
        ])

        self._main_window.register_view(
            "dashboard",
            lambda p: ReceptionistDashboard(p, stats, self._main_window.navigate_to),
        )
        self._main_window.register_view(
            "register_patient",
            lambda p: PatientRegistrationView(
                p, self._handle_register_patient,
                on_cancel=lambda: self._main_window.navigate_to("dashboard"),
            ),
        )
        self._main_window.register_view(
            "search_patient",
            lambda p: PatientSearchView(
                p, self._handle_search_patient,
                on_load_all=lambda: self._patient_ctrl.get_all_patients(limit=200),
            ),
        )
        self._main_window.register_view(
            "book_appointment",
            self._create_booking_view,
        )
        self._main_window.register_view(
            "appointments",
            lambda p: AppointmentListView(
                p, self._appt_ctrl.get_upcoming_appointments(),
                on_cancel=lambda aid: self._handle_cancel_appt(aid),
                on_refresh=lambda: self._main_window.navigate_to("appointments", force=True),
            ),
        )
        self._main_window.register_view("about", lambda p: AboutView(p))

        self._main_window.navigate_to("dashboard")

    # ── Patient management ─────────────────────────────────────

    def _handle_register_patient(self, data: Dict[str, Any]) -> None:
        """Process patient registration.

        Args:
            data: Form data from the patient registration view.
        """
        success, msg, pid = self._patient_ctrl.register_patient(
            data, audit_user_id=self._auth_ctrl.current_user_id,
        )
        if success:
            messagebox.showinfo("Success", msg)
            self._main_window.navigate_to("dashboard")
        else:
            messagebox.showerror("Error", msg)

    def _handle_search_patient(self, term: str) -> None:
        """Execute a patient search and display results inline.

        Args:
            term: The search term entered by the user.
        """
        success, msg, results = self._patient_ctrl.search_patients(term)
        view = self._main_window.get_current_content()
        if hasattr(view, "populate"):
            view.populate(results)
        else:
            parent = self._main_window._content_frame
            new_view = PatientSearchView(
                parent, self._handle_search_patient,
                on_load_all=lambda: self._patient_ctrl.get_all_patients(limit=200),
            )
            new_view.populate(results)
            self._main_window.show_content(new_view)

    # ── Appointment booking ────────────────────────────────────

    def _create_booking_view(self, parent: tk.Widget) -> AppointmentBookingView:
        """Build the appointment booking view with all callbacks wired.

        Args:
            parent: Parent tkinter widget.

        Returns:
            An AppointmentBookingView instance.
        """
        departments = self._doctor_ctrl.get_all_departments()
        patients = self._patient_ctrl.get_all_patients(limit=200)

        def _on_book(action: Any) -> None:
            if isinstance(action, tuple) and action[0] == "department_selected":
                dept_id = action[1]
                doctors = self._doctor_ctrl.get_doctors_by_department(dept_id)
                view.on_doctors_loaded(doctors)
            elif isinstance(action, tuple) and action[0] == "load_slots":
                _, doc_id, appt_date = action
                slots = self._appt_ctrl.get_available_slots(doc_id, appt_date)
                view.on_slots_loaded(slots)
            elif isinstance(action, tuple) and action[0] == "book":
                data: Dict[str, Any] = action[1]
                data["created_by"] = self._auth_ctrl.current_user_id
                success, msg, _ = self._appt_ctrl.book_appointment(
                    data, self._auth_ctrl.current_user_id,
                )
                if success:
                    view.show_success(msg)
                    self._main_window.navigate_to("dashboard")
                else:
                    view.show_error(msg)

        view = AppointmentBookingView(
            parent, departments, patients, _on_book,
            on_cancel=lambda: self._main_window.navigate_to("dashboard"),
        )
        return view

    # ── Appointment management ─────────────────────────────────

    def _handle_cancel_appt(self, appt_id: int) -> None:
        """Cancel an appointment and refresh the list.

        Args:
            appt_id: The appointment ID to cancel.
        """
        success, msg = self._appt_ctrl.cancel_appointment(
            appt_id, self._auth_ctrl.current_user_id,
        )
        if success:
            messagebox.showinfo("Success", msg)
        else:
            messagebox.showerror("Error", msg)
        self._main_window.navigate_to("appointments", force=True)
