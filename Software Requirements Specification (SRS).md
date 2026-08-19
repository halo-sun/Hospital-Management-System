# Software Requirements Specification (SRS)

## 1. Introduction

### 1.1 Purpose
The purpose of this Software Requirements Specification (SRS) document is to provide a detailed description of the **Scheduling System for Hospital Patient and Appointment Management**. It outlines the functional and non-functional requirements, system interfaces, and constraints that the software must adhere to during development and deployment.

### 1.2 Scope
The system is a desktop application designed to digitize hospital operations, specifically focusing on patient registration, appointment scheduling, and clinical record management. It aims to replace manual processes, reduce errors, and improve hospital workflow efficiency through a secure, role-based access system.

### 1.3 Definitions, Acronyms, and Abbreviations
* **UI/UX:** User Interface / User Experience
* **GUI:** Graphical User Interface
* **RBAC:** Role-Based Access Control
* **DB:** Database
* **ID:** Identifier
* **PDF:** Portable Document Format
* **Excel:** Microsoft Excel Spreadsheet

## 2. Overall Description

### 2.1 Product Perspective
The Scheduling System is a standalone desktop application built using Python 3.x and Tkinter, utilizing a MySQL database for persistent storage. It operates independently but may be expanded in the future to include mobile and web components.

### 2.2 Product Functions
The system provides the following core functions:
* **Authentication:** Secure login, password hashing, and session management.
* **Patient Management:** Registration, editing, searching, and medical history tracking.
* **Staff Management:** Management of doctors and receptionists, including role assignments.
* **Appointment Scheduling:** Booking, rescheduling, cancelling, and time-slot validation to prevent conflicts.
* **Clinical Records:** Diagnosis, prescriptions, and test report management.
* **Reporting & Analytics:** Generation of statistical reports and visual analytics dashboards.

### 2.3 User Classes and Characteristics
The system supports three distinct user classes:
* **Administrators:** Highly technical users responsible for system configuration, user management, and data analysis.
* **Receptionists:** Administrative staff responsible for front-desk operations, including patient registration and appointment scheduling.
* **Doctors:** Medical professionals responsible for patient consultations, diagnosis, and record updates.

### 2.4 Operating Environment
* **Hardware:** Standard desktop or laptop computer.
* **Operating System:** Windows, macOS, or Linux.
* **Software:** Python 3.x runtime, MySQL Server.

### 2.5 Design and Implementation Constraints
* The system must be developed using Python 3.x.
* The Graphical User Interface (GUI) must be built using Tkinter.
* The database must be MySQL, accessed via `mysql-connector-python`.
* The architecture must follow a clean design pattern (Controllers -> Services -> Repositories -> Database).

### 2.6 Assumptions and Dependencies
* It is assumed that the hospital has the necessary hardware and network infrastructure to run the application and connect to the MySQL database.
* The system depends on the availability of the MySQL database server.

## 3. Specific Requirements

### 3.1 Functional Requirements

#### 3.1.1 Authentication Module
* **FR1.1:** The system shall provide a secure login screen.
* **FR1.2:** The system shall hash user passwords using `bcrypt` before storing them in the database.
* **FR1.3:** The system shall authenticate users based on their assigned roles (Admin, Doctor, Receptionist).
* **FR1.4:** The system shall allow Administrators to reset user passwords.
* **FR1.5:** The system shall manage user sessions, including a session timeout feature.
* **FR1.6:** The system shall provide a secure logout function.

#### 3.1.2 Patient Management Module
* **FR2.1:** The system shall allow Receptionists to register new patients.
* **FR2.2:** The system shall auto-generate a unique Patient ID for each new patient.
* **FR2.3:** The system shall allow Receptionists to edit patient details.
* **FR2.4:** The system shall allow Administrators to delete patient records.
* **FR2.5:** The system shall provide a search function for patients by ID, name, or phone number.
* **FR2.6:** The system shall store and display patient medical history.
* **FR2.7:** The system shall store patient contact details and emergency contact information.

#### 3.1.3 Doctor and Staff Management Module
* **FR3.1:** The system shall allow Administrators to add, edit, and delete doctor profiles.
* **FR3.2:** The system shall allow Administrators to assign doctors to departments.
* **FR3.3:** The system shall allow Administrators to manage doctor availability and working hours.
* **FR3.4:** The system shall allow Administrators to manage receptionist accounts and user roles.

#### 3.1.4 Appointment Scheduling Module
* **FR4.1:** The system shall allow Receptionists to book appointments by selecting a patient, doctor, department, date, and time slot.
* **FR4.2:** The system shall implement strict time-slot validation to prevent overlapping appointments and double-bookings.
* **FR4.3:** The system shall ensure appointments are only booked within a doctor's working hours.
* **FR4.4:** The system shall account for doctor lunch breaks and hospital holidays when generating available slots.
* **FR4.5:** The system shall enforce a maximum number of appointments per doctor per day.
* **FR4.6:** The system shall allow Receptionists to view appointments, cancel appointments, and reschedule appointments.
* **FR4.7:** The system shall track appointment statuses (Booked, Completed, Cancelled, No Show).

#### 3.1.5 Clinical Records Module
* **FR5.1:** The system shall allow Doctors to view patient visit history.
* **FR5.2:** The system shall allow Doctors to add diagnoses and symptoms.
* **FR5.3:** The system shall allow Doctors to write and save prescriptions.
* **FR5.4:** The system shall allow Doctors to upload and store test reports.
* **FR5.5:** The system shall allow Doctors to set follow-up dates for patients.

#### 3.1.6 Search System Module
* **FR6.1:** The system shall provide a unified search interface to search by Patient ID, Patient name, Phone number, Doctor name, Appointment ID, or Department.

#### 3.1.7 Reports and Analytics Module
* **FR7.1:** The system shall generate reports for daily appointments, monthly appointments, doctor workload, patient count, and department statistics.
* **FR7.2:** The system shall allow exporting reports in PDF (using ReportLab) and Excel (using openpyxl) formats.
* **FR7.3:** The system shall provide an analytics dashboard with charts (using Matplotlib) for daily patients, weekly/monthly appointments, department performance, doctor utilization, peak hours, and cancellation rates.

### 3.2 Non-Functional Requirements

#### 3.2.1 Performance Requirements
* The system shall respond to user inputs within 2 seconds for standard operations (e.g., searching, saving records).
* The system shall handle concurrent database connections efficiently to prevent crashes.

#### 3.2.2 Security Requirements
* The system shall use parameterized SQL queries to prevent SQL injection attacks.
* The system shall enforce role-based access control (RBAC) to ensure users can only access authorized features.
* The system shall validate all user inputs on both the frontend and backend.
* The system shall log user activities in an `audit_logs` table for security tracking.

#### 3.2.3 Reliability and Availability
* The system shall gracefully handle errors such as database connection loss, invalid logins, and appointment conflicts without crashing.
* The system shall provide clear error messages to the user when an operation fails.

#### 3.2.4 Usability Requirements
* The system shall feature a modern, intuitive, and professional UI using Tkinter `ttk` widgets and custom themes.
* The system shall provide clear visual feedback for all actions (e.g., success messages, loading indicators).
* Navigation between modules shall be smooth and logical.

#### 3.2.5 Maintainability
* The system shall be developed using a clean architecture (Controllers -> Services -> Repositories -> Database) to ensure maintainability and scalability.
* All major functions and classes shall be documented using docstrings.

## 4. External Interface Requirements

### 4.1 User Interfaces
* The application will feature a GUI built with Python's Tkinter framework.
* It will include a Splash Screen, Login screen, Dashboards (Admin, Doctor, Receptionist), Patient Registration forms, Doctor Management tables, Appointment Booking calendars, and Analytics charts.

### 4.2 Hardware Interfaces
* The system interacts with standard input devices (keyboard, mouse) and output devices (monitor, printer for reports/slips).

### 4.3 Software Interfaces
* **MySQL Database:** The system interfaces with a MySQL database using `mysql-connector-python` for all data storage and retrieval.
* **ReportLab:** Used for generating PDF reports.
* **openpyxl:** Used for generating Excel reports.
* **Matplotlib:** Used for rendering analytics charts within the Tkinter GUI.
* **Pillow (PIL):** Used for image handling (e.g., doctor profile pictures, uploaded test reports).
* **tkcalendar:** Used for date selection in the appointment booking module.

### 4.4 Communication Interfaces
* N/A (The system is a standalone desktop application with local database connectivity).

## 5. System Features

### 5.1 Time-Slot Validation Logic
This is a critical system feature to prevent double-bookings.
1. User selects a Doctor and Date.
2. The system retrieves the Doctor's schedule and existing appointments for that date.
3. The system generates a list of available slots, accounting for working hours, lunch breaks, and holidays.
4. The Receptionist selects a slot.
5. The system checks for conflicts again immediately before saving.
6. If no conflict, the appointment is confirmed. If a conflict exists, an error is displayed, and the user must choose another slot.

### 5.2 Role-Based Dashboards
* **Admin Dashboard:** Focuses on user management, system configuration, and high-level analytics.
* **Receptionist Dashboard:** Focuses on patient registration, search, and appointment scheduling.
* **Doctor Dashboard:** Focuses on today's appointments, patient history, and clinical record entry.
