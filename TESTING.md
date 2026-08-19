# Testing Strategy and Plan

## 1. Introduction

The **Testing Strategy and Plan** document outlines the approach, methodologies, and procedures for testing the **Scheduling System for Hospital Patient and Appointment Management**. The primary goal of this strategy is to ensure that the application is reliable, secure, and functions according to the specifications defined in the Product Requirements Document (PRD) and Software Requirements Specification (SRS).

## 2. Testing Objectives

* **Functional Correctness:** Verify that all modules (Authentication, Patient Management, Appointment Scheduling, etc.) perform their intended functions accurately.
* **Data Integrity:** Ensure that the MySQL database maintains referential integrity and handles concurrent operations without corruption.
* **Security:** Validate that password hashing (`bcrypt`), role-based access control (RBAC), and parameterized SQL queries effectively prevent unauthorized access and SQL injection.
* **Performance:** Confirm that the application responds within acceptable timeframes and handles UI rendering smoothly.
* **User Experience:** Ensure the UI provides clear feedback and handles errors gracefully.

## 3. Testing Levels

The testing process will be conducted across multiple levels to ensure comprehensive coverage:

### 3.1 Unit Testing
* **Scope:** Individual functions and methods within the Service and Repository layers.
* **Focus:** Testing core logic in isolation. For example, testing the time-slot generation algorithm to ensure it correctly excludes lunch breaks and holidays.
* **Tools:** Python's built-in `unittest` or `pytest` framework.

### 3.2 Integration Testing
* **Scope:** Interactions between different modules and the database.
* **Focus:** Ensuring that data flows correctly from the GUI (Controllers) through the Services and Repositories to the MySQL database. For instance, verifying that a new patient registration correctly updates the `patients` table and logs the action in the `audit_logs` table.

### 3.3 System Testing
* **Scope:** The complete, integrated application.
* **Focus:** End-to-end testing of user workflows. For example, a Receptionist logs in, registers a patient, books an appointment, and then a Doctor logs in, views the appointment, and adds a prescription.

### 3.4 User Acceptance Testing (UAT)
* **Scope:** Final validation by stakeholders or simulated users.
* **Focus:** Ensuring the system meets the business objectives and is intuitive for the target user roles (Admin, Doctor, Receptionist).

## 4. Key Test Scenarios

### 4.1 Authentication and Security
* **Test Case 1.1:** Verify that a user cannot log in with an incorrect password.
* **Test Case 1.2:** Verify that passwords stored in the `users` table are hashed using `bcrypt` (i.e., plain text is not visible).
* **Test Case 1.3:** Verify that a Receptionist cannot access the Analytics Dashboard (RBAC enforcement).
* **Test Case 1.4:** Verify that the application handles SQL injection attempts gracefully (e.g., entering `' OR 1=1 --` in a login field).

### 4.2 Appointment Scheduling (Time-Slot Validation)
* **Test Case 2.1:** Verify that a Receptionist can successfully book an appointment within a doctor's working hours.
* **Test Case 2.2:** Verify that the system prevents booking an appointment during the doctor's lunch break.
* **Test Case 2.3:** Verify that the system prevents double-booking (selecting a slot that is already occupied by another patient).
* **Test Case 2.4:** Verify that the system enforces the maximum number of appointments per doctor per day.
* **Test Case 2.5:** Verify that the system blocks bookings on designated hospital holidays.

### 4.3 Patient and Clinical Records
* **Test Case 3.1:** Verify that a new patient is auto-assigned a unique Patient ID.
* **Test Case 3.2:** Verify that the system prevents the creation of duplicate patient records based on phone numbers.
* **Test Case 3.3:** Verify that a Doctor can successfully add a diagnosis and prescription to a visit record.
* **Test Case 3.4:** Verify that a Doctor can upload a test report (e.g., an image or PDF) and that it is stored correctly in the `test_reports` table.

### 4.4 Reporting and Analytics
* **Test Case 4.1:** Verify that the Analytics Dashboard correctly displays charts for daily patients and weekly appointments.
* **Test Case 4.2:** Verify that a report can be successfully exported to PDF format using ReportLab.
* **Test Case 4.3:** Verify that a report can be successfully exported to Excel format using `openpyxl`.

### 4.5 Error Handling and Edge Cases
* **Test Case 5.1:** Verify the system's behavior when the MySQL database connection is lost (e.g., server shutdown). The application should not crash but should display a clear error message.
* **Test Case 5.2:** Verify the system's behavior when invalid data is entered into forms (e.g., text in a date field).
* **Test Case 5.3:** Verify the behavior when attempting to delete a patient record that has existing appointments (should either restrict deletion or cascade appropriately based on design).

## 5. Test Environment

* **Hardware:** Standard desktop computer.
* **Operating System:** Windows 10/11, macOS, or Ubuntu Linux.
* **Software:**
  * Python 3.x runtime.
  * MySQL Server (local instance).
  * Required Python libraries (`mysql-connector-python`, `tkcalendar`, `matplotlib`, etc.).
* **Test Data:** A dedicated testing database (`hospital_test_db`) will be used, populated with mock data (dummy patients, doctors, and appointments) to ensure testing does not interfere with production data.

### 5.1 Packaging Verification (PyInstaller clean-VM check)

When the desktop app is bundled with PyInstaller, the clean-VM verification step **must explicitly exercise the analytics dashboard** (not just confirm the app launches):

* **matplotlib is a known PyInstaller trouble spot.** It bundles the wrong Tk backend, omits its data files (`mpl-data`), or silently drops numpy shared libs, so a build can pass smoke tests and still show blank analytics charts on the VM.
* **Verify on the clean VM:** open the Analytics dashboard and confirm all six charts draw with real data — not just that the window opens. Also confirm the startup log shows the dependency check passing (`check_critical_dependencies` in `src/app.py`) with no "Missing dependency" warnings.
* Do **not** assume bundling works because `pip install` fixed the dev environment; dev installs and PyInstaller bundling fail in different ways.

## 6. Defect Reporting

Defects identified during testing will be documented in a standard defect report format, including:
* **Defect ID:** Unique identifier.
* **Severity:** Critical, High, Medium, Low.
* **Description:** Detailed description of the issue.
* **Steps to Reproduce:** Clear instructions on how to recreate the error.
* **Expected Result:** What should have happened.
* **Actual Result:** What actually happened.
* **Screenshot/Logs:** Relevant evidence.

## 7. Sign-Off Criteria

The application will be considered ready for deployment when:
* All Critical and High severity defects have been resolved and verified.
* At least 90% of the defined test cases have passed.
* The system demonstrates stable performance under normal operating conditions.
* All security requirements (RBAC, password hashing, SQL injection prevention) have been validated.
