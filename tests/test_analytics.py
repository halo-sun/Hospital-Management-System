"""Unit tests for analytics — ReportService, ReportController, and export helpers.

Tests cover the analytics data methods, cancellation rate calculation,
and the PDF/Excel export function logic (without rendering actual files).
"""
from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock, patch
from typing import Any, Dict, List

import pytest

from src.services.report_service import ReportService


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def service() -> ReportService:
    """Create a ReportService with all repositories mocked."""
    with (
        patch("src.services.report_service.AppointmentRepository") as appt_cls,
        patch("src.services.report_service.PatientRepository") as pat_cls,
        patch("src.services.report_service.DoctorRepository") as doc_cls,
        patch("src.services.report_service.DepartmentRepository") as dept_cls,
        patch("src.services.report_service.VisitRecordRepository") as visit_cls,
    ):
        appt_cls.return_value = MagicMock()
        pat_cls.return_value = MagicMock()
        doc_cls.return_value = MagicMock()
        dept_cls.return_value = MagicMock()
        visit_cls.return_value = MagicMock()
        svc = ReportService()
        svc._appt_repo = appt_cls.return_value
        svc._patient_repo = pat_cls.return_value
        svc._doctor_repo = doc_cls.return_value
        svc._dept_repo = dept_cls.return_value
        svc._visit_repo = visit_cls.return_value
        yield svc


@pytest.fixture
def mock_appt(service: ReportService) -> MagicMock:
    """Access the mocked AppointmentRepository."""
    return service._appt_repo


@pytest.fixture
def mock_patient(service: ReportService) -> MagicMock:
    """Access the mocked PatientRepository."""
    return service._patient_repo


# ── Dashboard Stats ───────────────────────────────────────────


class TestDashboardStats:
    """Tests for get_dashboard_stats."""

    def test_stats_returns_counts(self, service: ReportService,
                                   mock_appt: MagicMock,
                                   mock_patient: MagicMock) -> None:
        """Dashboard stats returns aggregated counts."""
        mock_patient.count_all.return_value = 100
        service._doctor_repo.count_active.return_value = 10
        service._dept_repo.count_all.return_value = 8
        mock_appt.count_today.return_value = 25

        stats = service.get_dashboard_stats()
        assert stats["total_patients"] == 100
        assert stats["total_doctors"] == 10
        assert stats["total_departments"] == 8
        assert stats["today_appointments"] == 25


# ── Patient Registrations ─────────────────────────────────────


class TestPatientRegistrations:
    """Tests for get_patient_registrations."""

    def test_returns_daily_counts(self, service: ReportService,
                                   mock_patient: MagicMock) -> None:
        """get_patient_registrations delegates to repo."""
        mock_patient.count_registrations_by_date.return_value = [
            {"registration_date": date(2026, 6, 1), "count": 5},
        ]
        result = service.get_patient_registrations(
            date(2026, 6, 1), date(2026, 6, 30),
        )
        assert len(result) == 1
        assert result[0]["count"] == 5

    def test_empty_range(self, service: ReportService,
                          mock_patient: MagicMock) -> None:
        """Empty range returns empty list."""
        mock_patient.count_registrations_by_date.return_value = []
        result = service.get_patient_registrations(
            date(2026, 1, 1), date(2026, 1, 31),
        )
        assert result == []


# ── Cancellation Rate ─────────────────────────────────────────


class TestCancellationRate:
    """Tests for get_cancellation_rate."""

    def test_merges_cancelled_and_total(self, service: ReportService,
                                         mock_appt: MagicMock) -> None:
        """Cancellation rate merges two repo queries correctly."""
        mock_appt.count_cancelled_by_date_range.return_value = [
            {"appointment_date": date(2026, 6, 1), "count": 2},
            {"appointment_date": date(2026, 6, 2), "count": 1},
        ]
        mock_appt.count_total_by_date_range.return_value = [
            {"appointment_date": date(2026, 6, 1), "count": 10},
            {"appointment_date": date(2026, 6, 2), "count": 8},
        ]

        result = service.get_cancellation_rate(
            date(2026, 6, 1), date(2026, 6, 30),
        )
        assert len(result) == 2
        # Date 1: 2 cancelled out of 12 total (10+2) = 16.7%
        assert result[0]["appointment_date"] == date(2026, 6, 1)
        assert result[0]["total"] == 12
        assert result[0]["cancelled"] == 2
        assert result[0]["rate"] == 16.7

    def test_zero_cancellations(self, service: ReportService,
                                 mock_appt: MagicMock) -> None:
        """No cancellations returns 0% rate."""
        mock_appt.count_cancelled_by_date_range.return_value = []
        mock_appt.count_total_by_date_range.return_value = [
            {"appointment_date": date(2026, 6, 1), "count": 10},
        ]

        result = service.get_cancellation_rate(
            date(2026, 6, 1), date(2026, 6, 30),
        )
        assert len(result) == 1
        assert result[0]["rate"] == 0.0

    def test_zero_total_safe(self, service: ReportService,
                              mock_appt: MagicMock) -> None:
        """Zero total appointments does not cause division by zero."""
        mock_appt.count_cancelled_by_date_range.return_value = [
            {"appointment_date": date(2026, 6, 1), "count": 0},
        ]
        mock_appt.count_total_by_date_range.return_value = [
            {"appointment_date": date(2026, 6, 1), "count": 0},
        ]

        result = service.get_cancellation_rate(
            date(2026, 6, 1), date(2026, 6, 30),
        )
        assert len(result) == 1
        assert result[0]["rate"] == 0.0


# ── Monthly Appointments ──────────────────────────────────────


class TestMonthlyAppointments:
    """Tests for get_monthly_appointments."""

    def test_returns_monthly_breakdown(self, service: ReportService,
                                        mock_appt: MagicMock) -> None:
        """get_monthly_appointments returns daily counts and status."""
        mock_appt.count_by_date_range.return_value = [
            {"appointment_date": date(2026, 6, 1), "count": 5},
        ]
        mock_appt.count_by_status.return_value = [
            {"status": "Booked", "count": 3},
            {"status": "Completed", "count": 2},
        ]

        result = service.get_monthly_appointments(2026, 6)
        assert result["year"] == 2026
        assert result["month"] == 6
        assert len(result["daily_counts"]) == 1
        assert len(result["status_breakdown"]) == 2
        assert result["total"] == 5


# ── Get All Analytics ─────────────────────────────────────────


class TestGetAnalyticsData:
    """Tests for get_analytics_data."""

    def test_returns_all_keys(self, service: ReportService,
                               mock_appt: MagicMock,
                               mock_patient: MagicMock) -> None:
        """get_analytics_data returns all keys in one call."""
        mock_appt.count_by_date_range.return_value = []
        mock_appt.count_by_status.return_value = []
        mock_patient.count_registrations_by_date.return_value = []
        mock_appt.count_cancelled_by_date_range.return_value = []
        mock_appt.count_total_by_date_range.return_value = []
        mock_appt.count_by_hour.return_value = []
        mock_appt.get_doctor_workload.return_value = []
        mock_appt.count_by_department.return_value = []

        result = service.get_analytics_data(date(2026, 6, 1), date(2026, 6, 30))
        assert "daily_appointments" in result
        assert "patient_registrations" in result
        assert "doctor_workload" in result
        assert "department_stats" in result
        assert "cancellation_rate" in result
        assert "peak_hours" in result
        assert "status_breakdown" in result


# ── Export Helpers ────────────────────────────────────────────


class TestExportHelpers:
    """Tests for PDF and Excel export functions."""

    def test_export_excel_creates_workbook(self) -> None:
        """export_analytics_excel creates an .xlsx file."""
        from src.services.export_service import export_analytics_excel

        data = {
            "daily_appointments": {
                "daily_counts": [
                    {"appointment_date": date(2026, 6, 1), "count": 5},
                ],
                "total": 5,
            },
            "patient_registrations": [
                {"registration_date": date(2026, 6, 1), "count": 3},
            ],
            "doctor_workload": [
                {"doctor_name": "Dr. Smith", "department_name": "Cardiology", "appointment_count": 10},
            ],
            "department_stats": [
                {"department_name": "Cardiology", "count": 10},
            ],
            "cancellation_rate": [
                {"appointment_date": date(2026, 6, 1), "total": 10, "cancelled": 1, "rate": 10.0},
            ],
            "peak_hours": [
                {"hour": 9, "count": 5},
                {"hour": 10, "count": 8},
            ],
        }

        with patch("openpyxl.Workbook") as mock_wb_cls:
            mock_wb = MagicMock()
            mock_wb_cls.return_value = mock_wb
            mock_ws = MagicMock()
            mock_wb.active = mock_ws
            mock_wb.create_sheet.return_value = MagicMock()

            success, msg = export_analytics_excel(data, date(2026, 6, 1), date(2026, 6, 30), "/tmp/test.xlsx")
            assert success is True
            mock_wb.save.assert_called_once()

    def test_export_excel_failure(self) -> None:
        """export_analytics_excel handles errors gracefully."""
        from src.services.export_service import export_analytics_excel

        data = {}
        with patch("openpyxl.Workbook", side_effect=Exception("Mock error")):
            success, msg = export_analytics_excel(data, date(2026, 6, 1), date(2026, 6, 30), "/tmp/test.xlsx")
            assert success is False
            assert "failed" in msg.lower()

    def test_export_pdf_creates_document(self) -> None:
        """export_analytics_pdf creates a PDF with reportlab."""
        from src.services.export_service import export_analytics_pdf

        data = {
            "daily_appointments": {
                "daily_counts": [
                    {"appointment_date": date(2026, 6, 1), "count": 5},
                ],
                "total": 5,
            },
            "patient_registrations": [
                {"registration_date": date(2026, 6, 1), "count": 3},
            ],
            "doctor_workload": [
                {"doctor_name": "Dr. Smith", "department_name": "Cardiology", "appointment_count": 10},
            ],
            "department_stats": [
                {"department_name": "Cardiology", "count": 10},
            ],
            "cancellation_rate": [
                {"appointment_date": date(2026, 6, 1), "total": 10, "cancelled": 1, "rate": 10.0},
            ],
            "peak_hours": [
                {"hour": 9, "count": 5},
            ],
        }

        with patch("reportlab.platypus.SimpleDocTemplate") as mock_doc_cls:
            mock_doc = MagicMock()
            mock_doc_cls.return_value = mock_doc

            success, msg = export_analytics_pdf(data, date(2026, 6, 1), date(2026, 6, 30), "/tmp/test.pdf")
            assert success is True
            mock_doc.build.assert_called_once()

    def test_export_pdf_failure(self) -> None:
        """export_analytics_pdf handles errors gracefully."""
        from src.services.export_service import export_analytics_pdf

        data = {}
        with patch("reportlab.platypus.SimpleDocTemplate", side_effect=Exception("Mock error")):
            success, msg = export_analytics_pdf(data, date(2026, 6, 1), date(2026, 6, 30), "/tmp/test.pdf")
            assert success is False
            assert "failed" in msg.lower()


# ── Peak Hours ────────────────────────────────────────────────


class TestPeakHours:
    """Tests for get_peak_hours."""

    def test_returns_hourly_counts(self, service: ReportService,
                                    mock_appt: MagicMock) -> None:
        """get_peak_hours returns appointment distribution by hour."""
        mock_appt.count_by_hour.return_value = [
            {"hour": 9, "count": 5},
            {"hour": 10, "count": 8},
            {"hour": 11, "count": 12},
        ]
        result = service.get_peak_hours()
        assert len(result) == 3
        assert result[0]["hour"] == 9
        assert result[1]["count"] == 8


# ── Doctor Workload & Department Stats ────────────────────────


class TestDoctorAndDepartment:
    """Tests for doctor workload and department statistics."""

    def test_doctor_workload(self, service: ReportService,
                              mock_appt: MagicMock) -> None:
        """get_doctor_workload returns per-doctor counts."""
        mock_appt.get_doctor_workload.return_value = [
            {"doctor_name": "Dr. Smith", "department_name": "Cardiology", "appointment_count": 25},
        ]
        result = service.get_doctor_workload()
        assert len(result) == 1
        assert result[0]["doctor_name"] == "Dr. Smith"

    def test_department_stats(self, service: ReportService,
                               mock_appt: MagicMock) -> None:
        """get_department_statistics returns per-department counts."""
        mock_appt.count_by_department.return_value = [
            {"department_name": "Cardiology", "count": 50},
        ]
        result = service.get_department_statistics()
        assert len(result) == 1
        assert result[0]["department_name"] == "Cardiology"


# ── Existing method passthroughs ──────────────────────────────


class TestPassthroughMethods:
    """Tests that existing methods still work correctly."""

    def test_get_daily_appointments(self, service: ReportService,
                                     mock_appt: MagicMock) -> None:
        """get_daily_appointments delegates correctly."""
        mock_appt.find_by_date_range.return_value = [{"appointment_id": 1}]
        result = service.get_daily_appointments(date(2026, 6, 15))
        assert len(result) == 1

    def test_get_patient_gender_distribution(self, service: ReportService,
                                              mock_patient: MagicMock) -> None:
        """get_patient_gender_distribution returns gender counts."""
        mock_patient.count_by_gender.return_value = [
            {"gender": "Male", "count": 40},
            {"gender": "Female", "count": 60},
        ]
        result = service.get_patient_gender_distribution()
        assert len(result) == 2

    def test_get_recent_patients(self, service: ReportService,
                                  mock_patient: MagicMock) -> None:
        """get_recent_patients delegates correctly."""
        mock_patient.find_recent.return_value = [{"patient_id": "PAT-00001"}]
        result = service.get_recent_patients(5)
        assert len(result) == 1

    def test_get_appointment_status_report(self, service: ReportService,
                                            mock_appt: MagicMock) -> None:
        """get_appointment_status_report returns status counts."""
        mock_appt.count_by_status.return_value = [{"status": "Booked", "count": 10}]
        result = service.get_appointment_status_report()
        assert len(result) == 1
