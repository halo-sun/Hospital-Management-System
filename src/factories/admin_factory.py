"""Admin view factory – configures navigation and views for the Admin role.

Extracted from ``src.app.Application`` to give the admin
role-setup logic its own home and reduce the god-class problem.
"""
from __future__ import annotations

import logging
from typing import (
    Any, Callable, Dict, Optional,
)

import tkinter as tk
from tkinter import ttk, messagebox

from src.constants import Role
from src.controllers.auth_controller import AuthController
from src.controllers.doctor_controller import DoctorController
from src.controllers.staff_controller import StaffController
from src.controllers.appointment_controller import AppointmentController
from src.controllers.report_controller import ReportController
from src.controllers.audit_controller import AuditController
from src.controllers.settings_controller import SettingsController
from src.controllers.department_controller import DepartmentController
from src.gui.theme import Theme
from src.gui.main_window import MainWindow
from src.gui.admin.dashboard_view import AdminDashboard
from src.gui.admin.user_management_view import UserManagementView, CreateUserDialog
from src.gui.admin.doctor_management_view import DoctorManagementView, DoctorFormView
from src.gui.admin.department_management_view import DepartmentManagementView, DepartmentFormDialog
from src.gui.admin.staff_management_view import StaffManagementView, StaffFormDialog
from src.gui.admin.doctor_schedule_dialog import DoctorScheduleDialog, DoctorLeaveDialog
from src.gui.admin.analytics_dashboard_view import AnalyticsDashboardView
from src.gui.admin.audit_log_view import AuditLogView
from src.gui.admin.reports_view import ReportsView
from src.gui.admin.settings_view import SettingsView
from src.gui.receptionist.appointment_views import AppointmentListView
from src.gui.common.about_view import AboutView
from src.services.user_service import UserService
from src.services.staff_service import StaffService

logger = logging.getLogger(__name__)


class AdminViewFactory:
    """Creates and registers all admin-specific views with the main window.

    Encapsulates the view-construction callbacks, inline dialogs,
    and CRUD handlers that were previously mixed into ``Application``.
    """

    def __init__(
        self,
        main_window: MainWindow,
        auth_ctrl: AuthController,
        doctor_ctrl: DoctorController,
        staff_ctrl: StaffController,
        appt_ctrl: AppointmentController,
        report_ctrl: ReportController,
    ) -> None:
        """Initialise the factory with shared dependencies.

        Args:
            main_window: The application's main window.
            auth_ctrl: Authentication/authorisation controller.
            doctor_ctrl: Doctor management controller.
            staff_ctrl: Staff management controller.
            appt_ctrl: Appointment management controller.
            report_ctrl: Report/statistics controller.
        """
        self._main_window = main_window
        self._auth_ctrl = auth_ctrl
        self._doctor_ctrl = doctor_ctrl
        self._staff_ctrl = staff_ctrl
        self._appt_ctrl = appt_ctrl
        self._report_ctrl = report_ctrl
        self._audit_ctrl = AuditController(self._auth_ctrl)
        self._settings_ctrl = SettingsController(self._auth_ctrl)
        self._dept_ctrl = DepartmentController(self._auth_ctrl)
        self._user_service = UserService()
        self._staff_service = StaffService()

    def setup(self) -> None:
        """Register sidebar items and view factories for the admin."""
        stats = self._report_ctrl.get_dashboard_stats()

        self._main_window.set_sidebar_items([
            ("dashboard", "Dashboard"),
            ("manage_users", "Users"),
            ("manage_staff", "Staff"),
            ("manage_doctors", "Doctors"),
            ("manage_departments", "Departments"),
            ("appointments", "Appointments"),
            ("analytics", "Analytics"),
            ("reports", "Reports"),
            ("audit_logs", "Audit Logs"),
            ("settings", "Settings"),
            ("about", "About"),
        ])

        self._main_window.register_view(
            "dashboard",
            lambda p: AdminDashboard(p, stats, self._main_window.navigate_to),
        )
        self._main_window.register_view("manage_users", self._create_user_management_view)
        self._main_window.register_view("manage_staff", self._create_staff_management_view)
        self._main_window.register_view("manage_doctors", self._create_doctor_management_view)
        self._main_window.register_view("manage_departments", self._create_department_view)
        self._main_window.register_view("appointments", self._create_appointment_list_view)
        self._main_window.register_view("analytics", self._create_analytics_view)
        self._main_window.register_view("reports", self._create_reports_view)
        self._main_window.register_view("audit_logs", self._create_audit_log_view)
        self._main_window.register_view("settings", self._create_settings_view)
        self._main_window.register_view("about", lambda p: AboutView(p))

        self._main_window.navigate_to("dashboard")

    # ── User management ────────────────────────────────────────

    def _create_user_management_view(self, parent: tk.Widget) -> UserManagementView:
        """Build a populated user management view.

        Args:
            parent: Parent tkinter widget.

        Returns:
            A UserManagementView instance.
        """
        users = self._auth_ctrl.get_all_users()
        return UserManagementView(
            parent, users,
            on_create=lambda: self._show_create_user_dialog(parent),
            on_reset_password=lambda uid: self._handle_reset_password(uid, parent),
            on_refresh=lambda: self._main_window.navigate_to("manage_users", force=True),
        )

    def _show_create_user_dialog(self, parent: tk.Widget) -> None:
        """Open the create-user modal.

        Args:
            parent: Parent widget for the modal.
        """
        # Resolve role IDs once to avoid repeated DB round-trips
        role_ids = {
            rn: self._user_service.get_role_id(rn)
            for rn in (Role.ADMIN, Role.DOCTOR, Role.RECEPTIONIST)
        }
        roles = [
            {"role_id": rid, "role_name": rn}
            for rn, rid in role_ids.items()
            if rid
        ]

        CreateUserDialog(parent, roles, self._handle_create_user)

    def _handle_create_user(self, data: Dict[str, Any]) -> None:
        """Process user creation from the dialog.

        Args:
            data: Form data from the create-user dialog.
        """
        success, message, _ = self._auth_ctrl.create_user(data)
        if success:
            messagebox.showinfo("Success", message)
        else:
            messagebox.showerror("Error", message)

    def _handle_reset_password(self, user_id: int, parent: tk.Widget) -> None:
        """Show an inline password-reset dialog.

        Args:
            user_id: The target user's ID.
            parent: Parent widget.
        """
        dialog = tk.Toplevel(parent)
        dialog.title("Reset Password")
        dialog.geometry("360x200")
        dialog.configure(bg=Theme.BG)
        dialog.transient(parent)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=24, style="TFrame")
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="New Password", font=Theme.FONT_BODY).pack(anchor="w")
        pw_var = tk.StringVar()
        ttk.Entry(frame, textvariable=pw_var, width=35, font=Theme.FONT_BODY, show="*").pack(
            fill="x", pady=(2, 12)
        )

        ttk.Label(frame, text="Confirm Password", font=Theme.FONT_BODY).pack(anchor="w")
        confirm_var = tk.StringVar()
        ttk.Entry(frame, textvariable=confirm_var, width=35, font=Theme.FONT_BODY, show="*").pack(
            fill="x", pady=(2, 12)
        )

        def _submit() -> None:
            pw = pw_var.get()
            confirm = confirm_var.get()
            if pw != confirm:
                messagebox.showwarning("Warning", "Passwords do not match.", parent=dialog)
                return
            success, msg = self._auth_ctrl.reset_password(user_id, pw)
            if success:
                messagebox.showinfo("Success", msg, parent=dialog)
                dialog.destroy()
            else:
                messagebox.showerror("Error", msg, parent=dialog)

        tk.Button(
            frame, text="Reset", bg=Theme.WARNING, fg=Theme.WHITE,
            font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=16, pady=6,
            command=_submit,
        ).pack(pady=(8, 0))

    # ── Staff management ───────────────────────────────────────

    def _create_staff_management_view(self, parent: tk.Widget) -> StaffManagementView:
        """Build a populated staff management view.

        Args:
            parent: Parent tkinter widget.

        Returns:
            A StaffManagementView instance.
        """
        staff = self._staff_ctrl.get_all_staff()
        return StaffManagementView(
            parent, staff,
            on_add=lambda: self._show_add_staff_dialog(parent),
            on_edit=lambda uid: self._show_edit_staff_dialog(uid, parent),
            on_delete=lambda uid: self._handle_delete_staff(uid),
            on_activate=lambda uid: self._handle_activate_staff(uid),
            on_deactivate=lambda uid: self._handle_deactivate_staff(uid),
            on_refresh=lambda: self._main_window.navigate_to("manage_staff", force=True),
        )

    def _show_add_staff_dialog(self, parent: tk.Widget) -> None:
        """Open the add-staff modal.

        Args:
            parent: Parent widget.
        """
        role_ids = {
            rn: self._user_service.get_role_id(rn)
            for rn in (Role.DOCTOR, Role.RECEPTIONIST)
        }
        roles = [
            {"role_id": rid, "role_name": rn}
            for rn, rid in role_ids.items()
            if rid
        ]
        StaffFormDialog(parent, self._handle_add_staff, roles=roles)

    def _show_edit_staff_dialog(self, user_id: int, parent: tk.Widget) -> None:
        """Open the edit-staff modal.

        Args:
            user_id: The user to edit.
            parent: Parent widget.
        """
        staff = self._staff_ctrl.get_staff_member(user_id)
        if not staff:
            messagebox.showerror("Error", "Staff member not found.")
            return
        StaffFormDialog(parent, lambda d: self._handle_edit_staff(user_id, d), edit_data=staff)

    def _handle_add_staff(self, data: Dict[str, Any]) -> None:
        """Process staff creation.

        Args:
            data: Form data.
        """
        role_name = Role.RECEPTIONIST
        # If a role_id is included, look up the role name
        if data.get("role_id"):
            role_map = {
                rid: rn for rid, rn in [
                    (self._user_service.get_role_id(Role.DOCTOR), Role.DOCTOR),
                    (self._user_service.get_role_id(Role.RECEPTIONIST), Role.RECEPTIONIST),
                ]
            }
            role_name = role_map.get(data["role_id"], Role.RECEPTIONIST)

        success, msg, _ = self._staff_ctrl.create_staff(
            data, role_name=role_name, audit_user_id=self._auth_ctrl.current_user_id,
        )
        if success:
            messagebox.showinfo("Success", msg)
            self._main_window.navigate_to("manage_staff", force=True)
        else:
            messagebox.showerror("Error", msg)

    def _handle_edit_staff(self, user_id: int, data: Dict[str, Any]) -> None:
        """Process staff update.

        Args:
            user_id: The user ID.
            data: Updated form data.
        """
        success, msg = self._staff_ctrl.update_staff(
            user_id, data, audit_user_id=self._auth_ctrl.current_user_id,
        )
        if success:
            messagebox.showinfo("Success", msg)
            self._main_window.navigate_to("manage_staff", force=True)
        else:
            messagebox.showerror("Error", msg)

    def _handle_delete_staff(self, user_id: int) -> None:
        """Process staff deletion.

        Args:
            user_id: The user to delete.
        """
        success, msg = self._staff_ctrl.delete_staff(
            user_id, audit_user_id=self._auth_ctrl.current_user_id,
        )
        if success:
            messagebox.showinfo("Success", msg)
        else:
            messagebox.showerror("Error", msg)
        self._main_window.navigate_to("manage_staff", force=True)

    def _handle_activate_staff(self, user_id: int) -> None:
        """Activate a staff member.

        Args:
            user_id: The user ID.
        """
        success, msg = self._staff_ctrl.activate_staff(
            user_id, audit_user_id=self._auth_ctrl.current_user_id,
        )
        if success:
            messagebox.showinfo("Success", msg)
        else:
            messagebox.showerror("Error", msg)
        self._main_window.navigate_to("manage_staff", force=True)

    def _handle_deactivate_staff(self, user_id: int) -> None:
        """Deactivate a staff member.

        Args:
            user_id: The user ID.
        """
        success, msg = self._staff_ctrl.deactivate_staff(
            user_id, audit_user_id=self._auth_ctrl.current_user_id,
        )
        if success:
            messagebox.showinfo("Success", msg)
        else:
            messagebox.showerror("Error", msg)
        self._main_window.navigate_to("manage_staff", force=True)

    # ── Doctor management ──────────────────────────────────────

    def _create_doctor_management_view(self, parent: tk.Widget) -> DoctorManagementView:
        """Build a populated doctor management view with search/filter.

        Filtering is now handled client-side in the view -- the full
        doctor list is passed once and the view re-filters in-place on
        every dropdown change or search keystroke.  The callbacks below
        just trigger ``_apply_filters()`` on the live view instance
        rather than recreating the entire view.

        Args:
            parent: Parent tkinter widget.

        Returns:
            A DoctorManagementView instance.
        """
        doctors = self._doctor_ctrl.get_all_doctors()
        departments = self._dept_ctrl.list_departments()
        specializations = self._doctor_ctrl.get_all_specializations()

        def _refresh_view() -> None:
            """Re-fetch doctors from DB and refresh the current view."""
            view = self._main_window.get_current_content()
            if hasattr(view, "_apply_filters"):
                fresh = self._doctor_ctrl.get_all_doctors()
                view.populate(fresh)
            else:
                self._main_window.navigate_to("manage_doctors", force=True)

        return DoctorManagementView(
            parent, doctors, departments, specializations=specializations,
            on_add=lambda: self._show_add_doctor_form(parent),
            on_edit=lambda did: self._show_edit_doctor_form(did, parent),
            on_delete=lambda did: self._handle_delete_doctor(did),
            on_schedule=lambda did: self._show_doctor_schedule(did, parent),
            on_leave=lambda did: self._show_doctor_leave_dialog(did, parent),
            on_refresh=_refresh_view,
        )

    def _show_add_doctor_form(self, parent: tk.Widget) -> None:
        """Display the add-doctor form in the content area.

        Args:
            parent: Parent tkinter widget.
        """
        departments = self._dept_ctrl.list_departments()
        view = DoctorFormView(
            parent, departments, self._handle_add_doctor,
            on_cancel=lambda: self._main_window.navigate_to("manage_doctors", force=True),
        )
        self._main_window.show_content(view)

    def _show_edit_doctor_form(self, doctor_id: int, parent: tk.Widget) -> None:
        """Display the edit-doctor form in the content area.

        Args:
            doctor_id: The doctor to edit.
            parent: Parent tkinter widget.
        """
        doctor = self._doctor_ctrl.get_doctor(doctor_id)
        if not doctor:
            messagebox.showerror("Error", "Doctor not found.")
            return
        departments = self._dept_ctrl.list_departments()
        view = DoctorFormView(
            parent, departments,
            lambda d: self._handle_edit_doctor(doctor_id, d),
            on_cancel=lambda: self._main_window.navigate_to("manage_doctors", force=True),
            edit_data=doctor,
        )
        self._main_window.show_content(view)

    def _handle_add_doctor(self, data: Dict[str, Any]) -> None:
        """Process doctor creation from the form.

        Args:
            data: Form data.
        """
        user_data = None
        if data.get("username") and data.get("password"):
            user_data = {"username": data.pop("username"), "password": data.pop("password")}
        success, msg, _ = self._doctor_ctrl.create_doctor(data, user_data)
        if success:
            messagebox.showinfo("Success", msg)
            self._main_window.navigate_to("manage_doctors", force=True)
        else:
            messagebox.showerror("Error", msg)

    def _handle_edit_doctor(self, doctor_id: int, data: Dict[str, Any]) -> None:
        """Process doctor update from the form.

        Args:
            doctor_id: The doctor's ID.
            data: Updated form data.
        """
        success, msg = self._doctor_ctrl.update_doctor(doctor_id, data)
        if success:
            messagebox.showinfo("Success", msg)
            self._main_window.navigate_to("manage_doctors", force=True)
        else:
            messagebox.showerror("Error", msg)

    def _handle_delete_doctor(self, doctor_id: int) -> None:
        """Process doctor deletion.

        Args:
            doctor_id: The doctor to delete.
        """
        success, msg = self._doctor_ctrl.delete_doctor(doctor_id)
        if success:
            messagebox.showinfo("Success", msg)
        else:
            messagebox.showerror("Error", msg)
        self._main_window.navigate_to("manage_doctors", force=True)

    def _show_doctor_schedule(self, doctor_id: int, parent: tk.Widget) -> None:
        """Show the schedule editor for a doctor.

        Args:
            doctor_id: The doctor ID.
            parent: Parent widget.
        """
        doctor = self._doctor_ctrl.get_doctor(doctor_id)
        if not doctor:
            messagebox.showerror("Error", "Doctor not found.")
            return
        schedule = self._doctor_ctrl.get_doctor_schedule(doctor_id)
        doctor_name = doctor.get("full_name", "")

        def _on_save(day, start, end, available):
            """Save a single schedule entry."""
            return self._doctor_ctrl.update_doctor_schedule(
                doctor_id, day, start, end, available,
            )

        DoctorScheduleDialog(parent, doctor_name, schedule, _on_save)

    def _show_doctor_leave_dialog(self, doctor_id: int, parent: tk.Widget) -> None:
        """Show the leave editor for a doctor.

        Args:
            doctor_id: The doctor ID.
            parent: Parent widget.
        """
        doctor = self._doctor_ctrl.get_doctor(doctor_id)
        if not doctor:
            messagebox.showerror("Error", "Doctor not found.")
            return
        doctor_name = doctor.get("full_name", "")

        def _on_submit(data: Dict[str, Any]) -> None:
            data["doctor_id"] = doctor_id
            success, msg, _ = self._doctor_ctrl.add_doctor_leave(data)
            if success:
                messagebox.showinfo("Success", msg)
            else:
                messagebox.showerror("Error", msg)

        DoctorLeaveDialog(parent, doctor_name, _on_submit)

    # ── Department management ──────────────────────────────────

    def _create_department_view(self, parent: tk.Widget) -> DepartmentManagementView:
        """Build a populated department management view.

        Args:
            parent: Parent tkinter widget.

        Returns:
            A DepartmentManagementView instance.
        """
        departments = self._dept_ctrl.list_departments()
        return DepartmentManagementView(
            parent, departments,
            on_add=lambda: self._show_add_department_dialog(parent),
            on_edit=lambda did: self._show_edit_department_dialog(did, parent),
            on_delete=lambda did: self._handle_delete_department(did),
            on_refresh=lambda: self._main_window.navigate_to("manage_departments", force=True),
        )

    def _show_add_department_dialog(self, parent: tk.Widget) -> None:
        """Open the add-department modal.

        Args:
            parent: Parent widget.
        """
        DepartmentFormDialog(parent, self._handle_add_department)

    def _show_edit_department_dialog(self, dept_id: int, parent: tk.Widget) -> None:
        """Open the edit-department modal.

        Args:
            parent: Parent widget.
        """
        dept = self._dept_ctrl.get_department(dept_id)
        if not dept:
            messagebox.showerror("Error", "Department not found.")
            return
        DepartmentFormDialog(parent, lambda d: self._handle_edit_department(dept_id, d), edit_data=dept)

    def _handle_add_department(self, data: Dict[str, Any]) -> None:
        """Process department creation.

        Args:
            data: Form data.
        """
        success, msg, _ = self._dept_ctrl.create_department(
            data.get("department_name", ""), data.get("description", ""),
        )
        if success:
            messagebox.showinfo("Success", msg)
            self._main_window.navigate_to("manage_departments", force=True)
        else:
            messagebox.showerror("Error", msg)

    def _handle_edit_department(self, dept_id: int, data: Dict[str, Any]) -> None:
        """Process department update.

        Args:
            dept_id: The department ID.
            data: Updated form data.
        """
        success, msg = self._dept_ctrl.update_department(
            dept_id,
            department_name=data.get("department_name"),
            description=data.get("description"),
        )
        if success:
            messagebox.showinfo("Success", msg)
            self._main_window.navigate_to("manage_departments", force=True)
        else:
            messagebox.showerror("Error", msg)

    def _handle_delete_department(self, dept_id: int) -> None:
        """Process department deletion.

        Args:
            dept_id: The department ID.
        """
        success, msg = self._dept_ctrl.delete_department(dept_id)
        if success:
            messagebox.showinfo("Success", msg)
        else:
            messagebox.showerror("Error", msg)
        self._main_window.navigate_to("manage_departments", force=True)

    # ── Appointment / Reports ──────────────────────────────────

    def _create_appointment_list_view(self, parent: tk.Widget) -> AppointmentListView:
        """Build the upcoming-appointments list view.

        Args:
            parent: Parent tkinter widget.

        Returns:
            An AppointmentListView instance.
        """
        appointments = self._appt_ctrl.get_upcoming_appointments()
        return AppointmentListView(
            parent, appointments,
            on_cancel=lambda aid: self._handle_cancel_appt(aid),
            on_refresh=lambda: self._main_window.navigate_to("appointments", force=True),
        )

    def _handle_cancel_appt(self, appt_id: int) -> None:
        """Cancel an appointment and refresh the view.

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

    def _create_analytics_view(self, parent: tk.Widget) -> AnalyticsDashboardView:
        """Build the analytics dashboard view.

        Args:
            parent: Parent tkinter widget.

        Returns:
            An AnalyticsDashboardView instance.
        """
        return AnalyticsDashboardView(
            parent,
            on_load_data=lambda start, end: self._report_ctrl.get_analytics_data(start, end),
            on_export_pdf=lambda start, end, path: self._report_ctrl.export_analytics_pdf(
                start, end, path,
            ),
            on_export_excel=lambda start, end, path: self._report_ctrl.export_analytics_excel(
                start, end, path,
            ),
        )

    # ── Audit logs ────────────────────────────────────────────

    def _create_audit_log_view(self, parent: tk.Widget) -> AuditLogView:
        """Build the read-only audit log viewer.

        Args:
            parent: Parent tkinter widget.

        Returns:
            An AuditLogView instance.
        """
        return AuditLogView(
            parent,
            on_load_data=lambda start, end, action: self._audit_ctrl.list_audit_logs({
                "start_date": start,
                "end_date": end,
                "action": action,
            }),
        )

    # ── Settings ──────────────────────────────────────────────

    def _create_settings_view(self, parent: tk.Widget) -> SettingsView:
        """Build the admin settings view.

        Args:
            parent: Parent tkinter widget.

        Returns:
            A SettingsView instance.
        """
        return SettingsView(
            parent,
            on_get_theme=lambda: self._settings_ctrl.get_theme(),
            on_theme_changed=self._handle_theme_changed,
            on_load_holidays=lambda: self._settings_ctrl.list_holidays(),
            on_add_holiday=lambda d, desc: self._settings_ctrl.add_holiday(d, desc),
            on_remove_holiday=lambda hid: self._settings_ctrl.remove_holiday(hid),
            on_get_lockout=lambda: self._settings_ctrl.get_lockout_config(),
        )

    def _handle_theme_changed(self, theme_name: str) -> None:
        """Persist the chosen theme and refresh the whole window live.

        Args:
            theme_name: The newly selected theme name.
        """
        success, msg = self._settings_ctrl.set_theme(theme_name)
        if not success:
            messagebox.showerror("Error", msg)
            return
        self._main_window.refresh_theme()

    def _create_reports_view(self, parent: tk.Widget) -> ReportsView:
        """Build the dedicated reports view.

        Args:
            parent: Parent tkinter widget.

        Returns:
            A ReportsView instance.
        """
        return ReportsView(
            parent,
            on_generate=lambda rtype, start, end: (
                self._report_ctrl.generate_report(rtype, start, end)
            ),
            on_export_pdf=lambda fp, headers, rows, title, rtype: (
                self._report_ctrl.export_report_pdf(fp, headers, rows, title, rtype)
            ),
            on_export_excel=lambda fp, headers, rows, title, rtype: (
                self._report_ctrl.export_report_excel(fp, headers, rows, title, rtype)
            ),
        )
