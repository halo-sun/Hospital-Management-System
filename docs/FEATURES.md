# System Features Documentation

## 1. Introduction

The **Scheduling System for Hospital Patient and Appointment Management** is a comprehensive desktop application designed to streamline hospital operations. This document details the core features of the system, organized by functional modules, providing a clear understanding of the capabilities available to each user role.

## 2. Core Modules and Features

### 2.1 Module 1: Authentication

The Authentication module ensures secure access to the system and protects sensitive patient and hospital data.

* **Secure Login:** A dedicated login interface requiring valid credentials (username and password).
* **Password Hashing:** Implementation of the `bcrypt` library to securely hash passwords before storage in the database, ensuring that even if the database is compromised, passwords remain protected.
* **Role-Based Authentication:** The system authenticates users based on their assigned roles (Administrator, Doctor, Receptionist), dynamically loading the appropriate dashboard and granting specific permissions.
* **Forgot Password (Admin only):** A mechanism allowing Administrators to reset passwords for other users in case of forgotten credentials.
* **Session Management:** Active monitoring of user sessions, including session timeouts to automatically log out inactive users and prevent unauthorized access.
* **Logout:** A secure process to terminate the user session and clear cached data.

### 2.2 Module 2: Patient Management

This module allows Receptionists and Administrators to maintain a centralized database of patient information.

* **Register Patient:** A comprehensive form to capture new patient details, including personal information, contact details, and emergency contacts.
* **Auto-generate Patient ID:** The system automatically generates a unique, sequential Patient ID for every new registration, eliminating manual errors.
* **Edit Patient:** Functionality to update patient information, such as changing addresses or phone numbers.
* **Delete Patient (Admin only):** The ability for Administrators to remove patient records from the system, typically used for correcting erroneous entries.
* **Search Patient:** A robust search feature allowing users to find patients quickly using various criteria, including Patient ID, full name, or phone number.
* **Medical History:** A dedicated section to view and update a patient's past illnesses and medical conditions.
* **Contact Details:** Storage and management of primary contact information.
* **Emergency Contact:** Mandatory fields for capturing the name and phone number of a patient's emergency contact.

### 2.3 Module 3: Doctor Management

This module enables Administrators to manage the medical staff and their schedules.

* **Add Doctor:** A form to input new doctor details, including full name, specialization, and contact information.
* **Edit Doctor:** Functionality to update doctor profiles.
* **Delete Doctor:** The ability to remove doctor records.
* **Department Assignment:** Assigning doctors to specific hospital departments (e.g., Cardiology, Neurology).
* **Availability Management:** Setting the general availability of a doctor.
* **Working Hours:** Defining the specific start and end times of a doctor's working day, as well as their lunch break periods.

### 2.4 Module 4: Staff Management

This module handles the administrative users of the system.

* **Receptionist Management:** Adding, editing, and deleting receptionist accounts.
* **User Accounts:** General management of all user accounts within the system.
* **Roles:** Assigning specific roles (Admin, Doctor, Receptionist) to user accounts.
* **Permissions:** Configuring access rights based on assigned roles to ensure users can only access authorized features.

### 2.5 Module 5: Appointment Scheduling

This is the core module of the application, responsible for booking and managing patient appointments.

* **Select Patient:** Choosing an existing patient from the database.
* **Select Doctor:** Choosing the specific doctor the patient needs to see.
* **Select Department:** Filtering doctors by their department.
* **Select Date:** Using a calendar widget (`tkcalendar`) to choose the appointment date.
* **Select Available Slot:** The system dynamically generates and displays available time slots based on the selected doctor's schedule and existing bookings.
* **Confirm Booking:** Finalizing the appointment and saving it to the database.

**Validation Logic:**
* **No Overlapping Appointments:** The system prevents double-booking by ensuring no two appointments overlap for the same doctor.
* **Doctor Working Hours:** Appointments can only be scheduled within the defined working hours of the selected doctor.
* **Lunch Break:** The system automatically blocks out time slots during the doctor's designated lunch break.
* **Maximum Appointments/Day:** Enforces a cap on the number of appointments a doctor can have in a single day.
* **Holiday Validation:** The system checks against a list of hospital holidays and prevents booking on those dates.

### 2.6 Module 6: Appointment Management

This module provides tools for managing existing appointments.

* **View Appointments:** Displaying a list or calendar view of scheduled, completed, and cancelled appointments.
* **Cancel Appointment:** The ability to cancel a booked appointment, freeing up the time slot.
* **Reschedule Appointment:** Moving an appointment to a different date or time slot.
* **Appointment Status:** Tracking the current state of an appointment (Booked, Completed, Cancelled, No Show).

### 2.7 Module 7: Clinical Records

This module is primarily used by Doctors to document patient visits and treatments.

* **Visit History:** A chronological log of all past consultations for a specific patient.
* **Diagnosis:** Fields for the doctor to record the patient's medical diagnosis.
* **Symptoms:** Recording the symptoms reported by the patient during the visit.
* **Notes:** A free-text area for the doctor to add any additional observations or notes.
* **Prescription:** A structured interface for writing and saving medication prescriptions (medicine name, dosage, frequency, duration).
* **Test Report Upload:** The ability to attach digital files (e.g., PDFs, images) containing test results to the patient's visit record.
* **Follow-up Date:** Setting a recommended date for the patient's next visit.

### 2.8 Module 8: Search System

A unified search interface accessible across the application for quick data retrieval.

* **Search by Patient ID:** Direct lookup of a patient record.
* **Search by Patient Name:** Text-based search for patient names.
* **Search by Phone Number:** Lookup using the patient's contact number.
* **Search by Doctor:** Finding appointments or records associated with a specific doctor.
* **Search by Appointment ID:** Direct lookup of an appointment record.
* **Search by Department:** Filtering data by hospital department.

### 2.9 Module 9: Reports

This module generates statistical summaries of hospital operations.

* **Daily Appointments:** A summary of appointments scheduled for a specific day.
* **Monthly Appointments:** An aggregate view of appointments over a month.
* **Doctor Workload:** Metrics showing the number of patients seen by each doctor.
* **Patient Count:** Total number of registered patients.
* **Revenue Placeholder (Optional):** A section reserved for tracking appointment fees (if applicable).
* **Department Statistics:** Breakdown of patient volume by department.

**Export Options:**
* **PDF:** Exporting reports as Portable Document Format files using the ReportLab library.
* **Excel:** Exporting reports as spreadsheet files using the `openpyxl` library.

### 2.10 Module 10: Analytics Dashboard

A visual dashboard providing insights into hospital performance, primarily for Administrators.

* **Daily Patients:** A chart showing the number of patients visiting each day.
* **Weekly Appointments:** A trend line or bar chart of appointments over a week.
* **Monthly Appointments:** A chart showing monthly appointment trends.
* **Department Performance:** A comparison of patient volume across different departments.
* **Doctor Utilization:** Metrics showing how effectively doctor time is being utilized.
* **Peak Hours:** Identifying the busiest times of the day.
* **Cancellation Rate:** Tracking the percentage of appointments that are cancelled.

## 3. Future Scope Features

While not part of the initial release, the following features are planned for future development:
* Mobile App interface.
* Online Appointment Booking portal.
* SMS and Email Reminders for upcoming appointments.
* QR Check-in system.
* AI Slot Recommendation engine.
* Telemedicine integration.
* Face Recognition for patient identification.
* Cloud Database migration.
* Insurance Integration.
* Online Payment Gateway.
