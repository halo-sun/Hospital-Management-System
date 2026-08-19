# Project Rules and Guidelines

This document outlines the fundamental rules, conventions, and guidelines that must be followed during the development of the **Scheduling System for Hospital Patient and Appointment Management**.

## 1. Technology Stack Constraints

* **Programming Language:** Python 3.x must be used for all backend and frontend logic.
* **GUI Framework:** Tkinter is the mandatory framework for the desktop application interface. Modern UI styling using `ttk` and custom themes is highly recommended to ensure a polished user experience.
* **Database:** MySQL must be used as the primary relational database.
* **Database Connector:** `mysql-connector-python` is the required library for database interactions.
* **Architecture:** The project must strictly adhere to a clean architecture pattern: **Controllers → Services → Repositories → Database**. This ensures separation of concerns, maintainability, and scalability.

## 2. Security Rules

* **Password Hashing:** All user passwords (Admin, Doctor, Receptionist) must be hashed using the `bcrypt` library before being stored in the database. Plain-text passwords are strictly prohibited.
* **SQL Injection Prevention:** All database queries must use parameterized statements to prevent SQL injection vulnerabilities. Direct string concatenation for SQL queries is forbidden.
* **Role-Based Access Control (RBAC):** The system must enforce strict role-based permissions. Users must only access features relevant to their assigned role (Admin, Doctor, Receptionist).
* **Input Validation:** All user inputs (e.g., patient details, appointment slots) must be validated on the frontend and backend to prevent invalid data entry.
* **Session Management:** User sessions must be securely managed, including secure login, logout, and session timeout mechanisms.

## 3. Appointment Scheduling Rules

* **Time-Slot Validation:** This is a core requirement. The system must implement robust logic to prevent overlapping appointments and double-bookings.
* **Doctor Availability:** Appointments can only be booked within a doctor's defined working hours.
* **Lunch Breaks & Holidays:** The system must account for doctor lunch breaks and hospital holidays when generating available slots.
* **Maximum Appointments:** A maximum limit on the number of appointments per doctor per day must be enforced.
* **Validation Flow:**
  1. Select Doctor -> Select Date -> Retrieve Doctor Schedule -> Retrieve Existing Appointments -> Generate Available Slots.
  2. Receptionist selects a slot -> System checks again before saving -> Appointment Confirmed (or Slot Already Occupied error).

## 4. Database Rules

* **Centralized Records:** All patient records, medical histories, diagnoses, prescriptions, and test reports must be stored centrally in the MySQL database.
* **Audit Logging:** User activities (logins, data modifications, etc.) must be tracked in the `audit_logs` table for security and compliance.
* **Data Integrity:** Foreign key constraints must be used appropriately to maintain data integrity across related tables (e.g., linking appointments to patients and doctors).

## 5. UI/UX Rules

* **Modern Aesthetics:** Despite using Tkinter, the UI should be modern, intuitive, and professional. Utilize `ttk` widgets, consistent color schemes, and clear typography.
* **User Feedback:** The system must provide clear visual feedback for all actions (e.g., success messages, error alerts, loading indicators).
* **Navigation:** Navigation between different modules (Patient Registration, Doctor Management, Analytics, etc.) must be smooth and logical.

## 6. Error Handling Rules

* The application must handle common errors gracefully without crashing.
* Specific error scenarios must be addressed, including but not limited to:
  * Patient already exists
  * Doctor unavailable
  * Database connection lost
  * Invalid login credentials
  * Appointment conflicts
  * Duplicate phone numbers
  * Invalid report uploads

## 7. Reporting and Analytics Rules

* **Reports:** The system must generate daily, monthly, doctor workload, patient count, and department statistics reports.
* **Export Formats:** Reports must be exportable to PDF (using ReportLab) and Excel (using openpyxl).
* **Analytics Dashboard:** The dashboard must utilize Matplotlib to visualize key metrics such as daily patients, weekly/monthly appointments, department performance, doctor utilization, peak hours, and cancellation rates.

## 8. Code Quality Rules

* **Version Control:** Code must be committed regularly with clear, descriptive commit messages.
* **Documentation:** All major functions and classes must be documented using docstrings.
* **Testing:** Basic unit tests and integration tests should be implemented to ensure core functionalities work as expected.
* **Modularity:** Code should be modular and reusable, adhering to the defined clean architecture.
