# Scheduling System for Hospital Patient and Appointment Management

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## Project Overview
The **Scheduling System for Hospital Patient and Appointment Management** is a desktop-based hospital management application developed using Python, Tkinter, and MySQL. The system aims to replace manual appointment scheduling and patient record management with a centralized, secure, and efficient digital solution.

The software provides separate dashboards for **Administrators**, **Doctors**, and **Receptionists**, each with role-based access permissions. Receptionists can register patients and schedule appointments, doctors can view appointments and maintain clinical records, while administrators manage users, departments, doctors, reports, and analytics.

A key feature of the system is **time-slot validation**, ensuring that appointment conflicts and double-bookings are prevented. This helps reduce patient waiting times and improves overall hospital workflow.

The application also maintains medical history, diagnoses, prescriptions, and uploaded test reports. Analytical dashboards provide insights into patient flow, doctor workload, appointment trends, and hospital performance.

## Download

Pre-built Windows installer packages are available on the
[**Releases**](https://github.com/halo-sun/Hospital-Management-System/releases)
page. Download the latest `.exe` installer, run it, and follow the
on-screen wizard — no Python installation required.

For building from source or Linux/macOS development, see the
[Installation Guide](docs/INSTALL.md).

## Documentation

Detailed project documentation lives in the [`docs/`](docs/) folder:

| Document | Description |
|---|---|
| [PRD](docs/PRD.md) | Product Requirements Document |
| [SRS](docs/SRS.md) | Software Requirements Specification |
| [Architecture](docs/ARCHITECTURE.md) | System architecture & layered design |
| [Database Design](docs/DATABASE_DESIGN.md) | Schema, tables, indexes & cascade rules |
| [Features](docs/FEATURES.md) | Module-by-module feature documentation |
| [Testing](docs/TESTING.md) | Testing strategy & test plan |
| [UI/UX Guidelines](docs/UI_UX.md) | Design principles, layout & styling |
| [Project Rules](docs/PROJECT_RULES.md) | Coding conventions & security rules |
| [Roadmap](docs/ROADMAP.md) | Phased development plan |
| [Install Guide](docs/INSTALL.md) | Installer walkthrough & manual setup |

## Technology Stack

* **Programming Language:** Python 3.x
* **GUI Framework:** Tkinter
* **Database:** MySQL
* **Database Connector:** mysql-connector-python
* **Image Handling:** Pillow (PIL)
* **Charts & Analytics:** Matplotlib
* **Calendar Widget:** tkcalendar
* **Password Hashing:** bcrypt
* **Export Reports:** ReportLab (PDF) and openpyxl (Excel)

## Objectives

* Digitize hospital appointment scheduling.
* Eliminate manual scheduling errors.
* Reduce patient waiting time.
* Prevent double-booking through time-slot validation.
* Maintain centralized patient records.
* Secure sensitive medical data through role-based access.
* Improve hospital administration through analytics.

## Getting Started

### Prerequisites

* Python 3.x installed on your system.
* MySQL Server installed and running.
* Git (optional, for version control).

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/halo-sun/Hospital-Management-System.git
   cd Hospital-Management-System
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure the database connection:
   * Create a MySQL database (e.g., `hospital_db`).
   * Update the `database/config.py` (or equivalent) file with your MySQL credentials.

5. Run the application:
   ```bash
   python main.py
   ```

> **Note — analytics charts need matplotlib.** The analytics dashboard
> lazily imports matplotlib (and numpy) only when charts are drawn, so
> a missing install looks like a blank dashboard rather than a startup
> crash.  At startup the app logs a warning naming any missing critical
> dependency (see `check_critical_dependencies` in `src/app.py`), and
> each chart shows a distinct "Chart rendering unavailable — missing
> dependency" message instead of a silent blank area.  Run
> `pip install -r requirements.txt` if you see either.

## Project Structure

```
Hospital-Management-System/
├── assets/                  # Icons, images, and static resources
├── database/                # SQL schema, seeds, and migrations
├── docs/                    # Project documentation (PRD, SRS, etc.)
├── installer/               # Windows installer scripts (Inno Setup)
├── logs/                    # Application log files
├── reports/                 # Generated report exports
├── src/                     # Application source code
│   ├── auth/                #   Authentication & exceptions
│   ├── config/              #   Settings & configuration
│   ├── controllers/         #   Controller layer
│   ├── database/            #   Connection & schema init
│   ├── gui/                 #   Tkinter views & dashboards
│   ├── models/              #   Data models
│   ├── repositories/        #   Data access layer
│   ├── services/            #   Business logic layer
│   └── utils/               #   Helpers & utilities
├── tests/                   # Test suite (pytest)
├── main.py                  # Application entry point
├── requirements.txt         # Python dependencies
└── README.md
```

## Future Scope

* Mobile App integration
* Online Appointment Booking via web portal
* SMS & Email Reminders for appointments
* QR Check-in system
* AI-based Slot Recommendation
* Telemedicine integration
* Face Recognition for patient identification
* Cloud Database migration
* Insurance Integration
* Online Payment Gateway

## License

This project is licensed under the MIT License - see the LICENSE file for details.
