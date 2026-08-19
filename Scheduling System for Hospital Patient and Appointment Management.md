# Scheduling System for Hospital Patient and Appointment Management

## Project Overview
The **Scheduling System for Hospital Patient and Appointment Management** is a desktop-based hospital management application developed using Python, Tkinter, and MySQL. The system aims to replace manual appointment scheduling and patient record management with a centralized, secure, and efficient digital solution.

The software provides separate dashboards for **Administrators**, **Doctors**, and **Receptionists**, each with role-based access permissions. Receptionists can register patients and schedule appointments, doctors can view appointments and maintain clinical records, while administrators manage users, departments, doctors, reports, and analytics.

A key feature of the system is **time-slot validation**, ensuring that appointment conflicts and double-bookings are prevented. This helps reduce patient waiting times and improves overall hospital workflow.

The application also maintains medical history, diagnoses, prescriptions, and uploaded test reports. Analytical dashboards provide insights into patient flow, doctor workload, appointment trends, and hospital performance.

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
   git clone https://github.com/your-username/HospitalSchedulingSystem.git
   cd HospitalSchedulingSystem
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

## Project Structure

```
HospitalSchedulingSystem/
├── assets/
├── config/
├── database/
├── docs/
├── logs/
├── reports/
├── src/
│   ├── authentication/
│   ├── controllers/
│   ├── database/
│   ├── gui/
│   ├── models/
│   ├── repositories/
│   ├── services/
│   ├── utils/
│   └── analytics/
├── tests/
├── main.py
├── requirements.txt
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
