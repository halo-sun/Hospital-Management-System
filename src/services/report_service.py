"""Report service for generating statistics and export data."""
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple
from src.repositories.appointment_repository import AppointmentRepository
from src.repositories.patient_repository import PatientRepository
from src.repositories.doctor_repository import DoctorRepository, DepartmentRepository
from src.repositories.clinical_repository import VisitRecordRepository

logger = logging.getLogger(__name__)


class ReportService:
    """Generates statistical reports and data summaries for the analytics dashboard."""

    def __init__(self) -> None:
        """Initialize ReportService with required repositories."""
        self._appt_repo = AppointmentRepository()
        self._patient_repo = PatientRepository()
        self._doctor_repo = DoctorRepository()
        self._dept_repo = DepartmentRepository()
        self._visit_repo = VisitRecordRepository()

    # ── Summary Statistics ─────────────────────────────────────

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get summary statistics for the admin dashboard.

        Returns:
            Dictionary with total_patients, total_doctors, today_appointments, etc.
        """
        return {
            "total_patients": self._patient_repo.count_all(),
            "total_doctors": self._doctor_repo.count_active(),
            "total_departments": self._dept_repo.count_all(),
            "today_appointments": self._appt_repo.count_today(),
        }

    # ── Appointment Reports ────────────────────────────────────

    def get_daily_appointments(self, target_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """Get all appointments for a specific day.

        Args:
            target_date: The date to report on (defaults to today).

        Returns:
            List of appointment records for the day.
        """
        if target_date is None:
            target_date = date.today()
        return self._appt_repo.find_by_doctor_and_date(0, target_date) \
            if False else self._appt_repo.find_by_date_range(target_date, target_date)

    def get_monthly_appointments(
        self, year: Optional[int] = None, month: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get appointment statistics for a month.

        Args:
            year: The year (defaults to current year).
            month: The month (defaults to current month).

        Returns:
            Dictionary with daily_counts, total, and status_breakdown.
        """
        now = datetime.now()
        year = year or now.year
        month = month or now.month

        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(year, month + 1, 1) - timedelta(days=1)

        daily = self._appt_repo.count_by_date_range(start, end)
        status = self._appt_repo.count_by_status()

        return {
            "year": year,
            "month": month,
            "daily_counts": daily,
            "status_breakdown": status,
            "total": sum(d.get("count", 0) for d in daily),
        }

    def get_appointment_status_report(self) -> List[Dict[str, Any]]:
        """Get appointment counts grouped by status.

        Returns:
            List of dicts with 'status' and 'count'.
        """
        return self._appt_repo.count_by_status()

    # ── Doctor Reports ─────────────────────────────────────────

    def get_doctor_workload(self) -> List[Dict[str, Any]]:
        """Get appointment counts per doctor.

        Returns:
            List of dicts with doctor info and appointment count.
        """
        return self._appt_repo.get_doctor_workload()

    def get_department_statistics(self) -> List[Dict[str, Any]]:
        """Get appointment counts per department.

        Returns:
            List of dicts with 'department_name' and 'count'.
        """
        return self._appt_repo.count_by_department()

    # ── Patient Reports ────────────────────────────────────────

    def get_patient_count(self) -> int:
        """Get total number of registered patients.

        Returns:
            Total patient count.
        """
        return self._patient_repo.count_all()

    def get_patient_gender_distribution(self) -> List[Dict[str, Any]]:
        """Get patient count grouped by gender.

        Returns:
            List of dicts with 'gender' and 'count'.
        """
        return self._patient_repo.count_by_gender()

    def get_recent_patients(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recently registered patients.

        Args:
            limit: Number of records.

        Returns:
            List of recent patient records.
        """
        return self._patient_repo.find_recent(limit)

    # ── Peak Hours ─────────────────────────────────────────────

    def get_peak_hours(self) -> List[Dict[str, Any]]:
        """Get appointment distribution by hour of day.

        Returns:
            List of dicts with 'hour' and 'count'.
        """
        return self._appt_repo.count_by_hour()

    # ── Patient Registrations ───────────────────────────────────

    def get_patient_registrations(
        self, start_date: date, end_date: date,
    ) -> List[Dict[str, Any]]:
        """Get patient registration counts by date.

        Args:
            start_date: Range start.
            end_date: Range end.

        Returns:
            List of dicts with 'registration_date' and 'count'.
        """
        return self._patient_repo.count_registrations_by_date(start_date, end_date)

    # ── Cancellation Rate ───────────────────────────────────────

    def get_cancellation_rate(
        self, start_date: date, end_date: date,
    ) -> List[Dict[str, Any]]:
        """Get cancellation rate per date within a range.

        Returns a list of date records with total appointments,
        cancelled count, and cancellation percentage.

        Args:
            start_date: Range start.
            end_date: Range end.

        Returns:
            List of dicts with 'appointment_date', 'total', 'cancelled', 'rate'.
        """
        cancelled = self._appt_repo.count_cancelled_by_date_range(start_date, end_date)
        total = self._appt_repo.count_total_by_date_range(start_date, end_date)

        # Merge into date-keyed map
        cancel_map: Dict[date, int] = {
            r["appointment_date"]: r["count"] for r in cancelled
        }
        total_map: Dict[date, int] = {
            r["appointment_date"]: r["count"] for r in total
        }

        all_dates = set(list(cancel_map.keys()) + list(total_map.keys()))
        result = []
        for dt in sorted(all_dates):
            t = total_map.get(dt, 0)
            c = cancel_map.get(dt, 0)
            total_count = t + c  # include cancelled in total
            rate = round((c / total_count * 100) if total_count > 0 else 0, 1)
            result.append({
                "appointment_date": dt,
                "total": total_count,
                "cancelled": c,
                "rate": rate,
            })
        return result

    # ── Date Range Helper ───────────────────────────────────────

    def get_analytics_data(
        self, start_date: date, end_date: date,
    ) -> Dict[str, Any]:
        """Get all analytics data for a date range in one call.

        Reduces redundant DB queries by fetching all needed data
        at once for the analytics dashboard.

        Args:
            start_date: Range start.
            end_date: Range end.

        Returns:
            Dictionary with keys: daily_appointments, patient_registrations,
            doctor_workload, department_stats, cancellation_rate, peak_hours.
        """
        return {
            "daily_appointments": self.get_date_range_report(start_date, end_date),
            "patient_registrations": self.get_patient_registrations(start_date, end_date),
            "doctor_workload": self.get_doctor_workload(),
            "department_stats": self.get_department_statistics(),
            "cancellation_rate": self.get_cancellation_rate(start_date, end_date),
            "peak_hours": self.get_peak_hours(),
            "status_breakdown": self.get_appointment_status_report(),
        }

    # ── Date Range Reports ─────────────────────────────────────

    def get_date_range_report(
        self, start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """Generate a comprehensive report for a date range.

        Args:
            start_date: Range start date.
            end_date: Range end date.

        Returns:
            Dictionary with daily_counts, total, and date range info.
        """
        daily = self._appt_repo.count_by_date_range(start_date, end_date)
        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "daily_counts": daily,
            "total": sum(d.get("count", 0) for d in daily),
        }

    # ── Analytics Export ────────────────────────────────────────

    def export_analytics_pdf(
        self, start_date: date, end_date: date, filepath: str,
        chart_paths=None,
    ) -> Tuple[bool, str]:
        """Export analytics dashboard to a PDF file.

        Gathers data for the date range and delegates to the
        PDF layout helper.  Chart snapshots can be embedded by
        passing PNG file paths.

        Args:
            start_date: Report start date.
            end_date: Report end date.
            filepath: Destination file path.
            chart_paths: Optional list of PNG paths to embed.

        Returns:
            Tuple of (success, message).
        """
        from src.services.export_service import export_analytics_pdf as _do_pdf
        data = self.get_analytics_data(start_date, end_date)
        return _do_pdf(data, start_date, end_date, filepath, chart_paths=chart_paths)

    def export_analytics_excel(
        self, start_date: date, end_date: date, filepath: str,
    ) -> Tuple[bool, str]:
        """Export analytics data to an Excel workbook.

        Gathers data for the date range and delegates to the
        Excel layout helper.

        Args:
            start_date: Report start date.
            end_date: Report end date.
            filepath: Destination file path.

        Returns:
            Tuple of (success, message).
        """
        from src.services.export_service import export_analytics_excel as _do_xlsx
        data = self.get_analytics_data(start_date, end_date)
        return _do_xlsx(data, start_date, end_date, filepath)

    # ── Export Helpers ──────────────────────────────────────────

    def prepare_export_data(
        self, report_type: str, **kwargs: Any
    ) -> Tuple[List[str], List[List[Any]], str]:
        """Prepare data for export to PDF or Excel.

        Args:
            report_type: Type of report to generate.
            **kwargs: Additional parameters for the report.

        Returns:
            Tuple of (headers, rows, title).
        """
        if report_type == "daily_appointments":
            return self._prepare_daily_export(**kwargs)
        elif report_type == "monthly_appointments":
            return self._prepare_monthly_export(**kwargs)
        elif report_type == "doctor_workload":
            return self._prepare_doctor_workload_export()
        elif report_type == "department_stats":
            return self._prepare_department_export()
        else:
            return [], [], "Report"

    def _prepare_daily_export(
        self, target_date: Optional[date] = None, **kwargs: Any
    ) -> Tuple[List[str], List[List[Any]], str]:
        """Prepare daily appointment export data.

        Args:
            target_date: The date to export.

        Returns:
            Tuple of (headers, rows, title).
        """
        target_date = target_date or date.today()
        records = self.get_daily_appointments(target_date)
        headers = ["ID", "Patient", "Doctor", "Time", "Status", "Department"]
        rows = []
        for r in records:
            rows.append([
                r.get("appointment_id", ""),
                r.get("patient_name", ""),
                r.get("doctor_name", ""),
                f"{r.get('start_time', '')} - {r.get('end_time', '')}",
                r.get("status", ""),
                r.get("department_name", ""),
            ])
        title = f"Daily Appointments - {target_date.strftime('%B %d, %Y')}"
        return headers, rows, title

    def _prepare_monthly_export(
        self, year: Optional[int] = None, month: Optional[int] = None, **kwargs: Any
    ) -> Tuple[List[str], List[List[Any]], str]:
        """Prepare monthly appointment export data.

        Args:
            year: The year.
            month: The month.

        Returns:
            Tuple of (headers, rows, title).
        """
        data = self.get_monthly_appointments(year, month)
        headers = ["Date", "Appointments"]
        rows = [[d.get("appointment_date", ""), d.get("count", 0)] for d in data["daily_counts"]]
        title = f"Monthly Report - {data['year']}/{data['month']:02d}"
        return headers, rows, title

    def _prepare_doctor_workload_export(self) -> Tuple[List[str], List[List[Any]], str]:
        """Prepare doctor workload export data.

        Returns:
            Tuple of (headers, rows, title).
        """
        records = self.get_doctor_workload()
        headers = ["Doctor", "Department", "Appointments"]
        rows = [
            [r.get("doctor_name", ""), r.get("department_name", ""), r.get("appointment_count", 0)]
            for r in records
        ]
        return headers, rows, "Doctor Workload Report"

    def _prepare_department_export(self) -> Tuple[List[str], List[List[Any]], str]:
        """Prepare department statistics export data.

        Returns:
            Tuple of (headers, rows, title).
        """
        records = self.get_department_statistics()
        headers = ["Department", "Appointments"]
        rows = [[r.get("department_name", ""), r.get("count", 0)] for r in records]
        return headers, rows, "Department Statistics Report"
