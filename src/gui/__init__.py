"""GUI package for Hospital Management System.

Contains all Tkinter-based user interface components organised
by user role:

- ``auth/``       – Login screen
- ``common/``     – Shared base classes and reusable widgets
- ``admin/``      – Administrator dashboards and management views
- ``doctor/``     – Doctor-specific views
- ``receptionist/`` – Receptionist patient and appointment views
"""
from src.gui.theme import Theme
from src.gui.main_window import MainWindow

__all__ = [
    "Theme",
    "MainWindow",
]
