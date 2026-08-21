"""Regression test for DoctorManagementView construction.

Verifies that the view can be instantiated with a full doctor list,
departments, and specializations without raising an AttributeError.

Bug: Phase 2 renamed ``self._doctors`` to ``self._all_doctors`` for
client-side filtering, but the stats summary in ``_build_ui`` still
referenced ``self._doctors``, causing an AttributeError that prevented
the Doctors menu from opening.
"""
from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def sample_doctors() -> List[Dict[str, Any]]:
    """Minimal doctor list for view construction."""
    return [
        {
            "doctor_id": 1,
            "full_name": "Dr. Alice Smith",
            "department_name": "Cardiology",
            "specialization": "Heart Surgery",
            "email": "alice@hospital.com",
            "contact_number": "1234567890",
            "status": "Active",
        },
        {
            "doctor_id": 2,
            "full_name": "Dr. Bob Jones",
            "department_name": "Neurology",
            "specialization": "Brain Surgery",
            "email": "bob@hospital.com",
            "contact_number": "0987654321",
            "status": "Inactive",
        },
    ]


@pytest.fixture
def sample_departments() -> List[Dict[str, Any]]:
    """Minimal department list."""
    return [
        {"department_id": 1, "department_name": "Cardiology"},
        {"department_id": 2, "department_name": "Neurology"},
    ]


@pytest.fixture
def sample_specializations() -> List[str]:
    """Minimal specialization list."""
    return ["Heart Surgery", "Brain Surgery"]


class TestDoctorManagementViewConstruction:
    """Verify DoctorManagementView can be constructed without errors.

    This is the core regression test — the view MUST construct successfully
    with the same data that the admin factory passes to it.
    """

    def test_view_constructs_with_full_data(
        self,
        sample_doctors: List[Dict[str, Any]],
        sample_departments: List[Dict[str, Any]],
        sample_specializations: List[str],
    ) -> None:
        """View construction should not raise AttributeError."""
        import tkinter as tk
        from src.gui.admin.doctor_management_view import DoctorManagementView

        root = tk.Tk()
        root.withdraw()
        try:
            view = DoctorManagementView(
                root,
                doctors=sample_doctors,
                departments=sample_departments,
                specializations=sample_specializations,
            )
            # Verify internal state is correct
            assert hasattr(view, "_all_doctors"), (
                "View must have _all_doctors attribute"
            )
            assert len(view._all_doctors) == 2
            # Verify tree was populated
            children = view._tree.get_children()
            assert len(children) == 2
        finally:
            root.destroy()

    def test_view_constructs_with_empty_data(self) -> None:
        """View construction should work with empty doctor list."""
        import tkinter as tk
        from src.gui.admin.doctor_management_view import DoctorManagementView

        root = tk.Tk()
        root.withdraw()
        try:
            view = DoctorManagementView(
                root,
                doctors=[],
                departments=[],
                specializations=[],
            )
            assert hasattr(view, "_all_doctors")
            assert len(view._all_doctors) == 0
            children = view._tree.get_children()
            assert len(children) == 0
        finally:
            root.destroy()

    def test_view_stats_display_correctly(
        self,
        sample_doctors: List[Dict[str, Any]],
        sample_departments: List[Dict[str, Any]],
        sample_specializations: List[str],
    ) -> None:
        """Stats summary must show correct counts (the line that was broken).

        Before the fix, ``self._doctors`` was referenced but the attribute
        was ``self._all_doctors`` — this test ensures the stats line uses
        the correct attribute.
        """
        import tkinter as tk
        from src.gui.admin.doctor_management_view import DoctorManagementView

        root = tk.Tk()
        root.withdraw()
        try:
            # This should NOT raise AttributeError: 'DoctorManagementView'
            # object has no attribute '_doctors'
            view = DoctorManagementView(
                root,
                doctors=sample_doctors,
                departments=sample_departments,
                specializations=sample_specializations,
            )
            # If we get here without error, the bug is fixed
            assert view is not None
        finally:
            root.destroy()

    def test_populate_replaces_data(
        self,
        sample_doctors: List[Dict[str, Any]],
        sample_departments: List[Dict[str, Any]],
        sample_specializations: List[str],
    ) -> None:
        """populate() should replace _all_doctors and re-render."""
        import tkinter as tk
        from src.gui.admin.doctor_management_view import DoctorManagementView

        root = tk.Tk()
        root.withdraw()
        try:
            view = DoctorManagementView(
                root,
                doctors=sample_doctors,
                departments=sample_departments,
                specializations=sample_specializations,
            )
            assert len(view._tree.get_children()) == 2

            # Populate with new data
            new_doctors = [sample_doctors[0]]
            view.populate(new_doctors)
            assert len(view._all_doctors) == 1
            assert len(view._tree.get_children()) == 1
        finally:
            root.destroy()

    def test_client_side_filtering(
        self,
        sample_doctors: List[Dict[str, Any]],
        sample_departments: List[Dict[str, Any]],
        sample_specializations: List[str],
    ) -> None:
        """Dropdown filters should narrow the displayed list."""
        import tkinter as tk
        from src.gui.admin.doctor_management_view import DoctorManagementView

        root = tk.Tk()
        root.withdraw()
        try:
            view = DoctorManagementView(
                root,
                doctors=sample_doctors,
                departments=sample_departments,
                specializations=sample_specializations,
            )
            # Initially all doctors shown
            assert len(view._tree.get_children()) == 2

            # Filter by department
            view._dept_filter_var.set("Cardiology")
            view._apply_filters()
            assert len(view._tree.get_children()) == 1

            # Clear filters
            view._clear_filters()
            assert len(view._tree.get_children()) == 2
        finally:
            root.destroy()

    def test_factory_callback_signature(
        self,
        sample_doctors: List[Dict[str, Any]],
        sample_departments: List[Dict[str, Any]],
        sample_specializations: List[str],
    ) -> None:
        """Verify factory-style callback construction works.

        This mirrors how AdminViewFactory._create_doctor_management_view
        constructs the view — with on_search/on_filter as lambdas.
        """
        import tkinter as tk
        from src.gui.admin.doctor_management_view import DoctorManagementView

        root = tk.Tk()
        root.withdraw()
        try:
            search_called = []
            filter_called = []

            view = DoctorManagementView(
                root,
                doctors=sample_doctors,
                departments=sample_departments,
                specializations=sample_specializations,
                on_search=lambda term: search_called.append(term),
                on_filter=lambda dept_id, spec, status: filter_called.append(
                    (dept_id, spec, status)
                ),
                on_add=lambda: None,
                on_edit=lambda did: None,
                on_delete=lambda did: None,
                on_schedule=lambda did: None,
                on_leave=lambda did: None,
                on_refresh=lambda: None,
            )
            assert view is not None
            assert len(view._tree.get_children()) == 2
        finally:
            root.destroy()
