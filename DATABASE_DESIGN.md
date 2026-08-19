# Database Design

## 1. Overview

The **Scheduling System for Hospital Patient and Appointment Management** utilizes a MySQL database to store all persistent data. The database design is centered around maintaining the integrity of patient records, doctor schedules, and appointment history while ensuring efficient retrieval for reporting and analytics.

The database consists of several interconnected tables, utilizing foreign keys to enforce referential integrity. All sensitive data, such as user passwords, are hashed before storage.

## 2. Entity-Relationship Summary

* A **User** belongs to one **Role** (Admin, Doctor, Receptionist).
* A **User** who is a Doctor has a corresponding record in the **Doctors** table.
* A **Doctor** belongs to one or more **Departments**.
* A **Patient** can have multiple **Appointments**.
* An **Appointment** links a **Patient**, a **Doctor**, and a specific time slot.
* A **Doctor** has multiple **Visit Records**, which contain **Diagnoses**, **Prescriptions**, and **Test Reports**.
* Every significant action by a **User** is recorded in the **Audit Logs**.

## 3. Table Definitions

### 3.1 `roles`
Stores the system roles available to users.

| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `role_id` | INT | PRIMARY KEY, AUTO_INCREMENT | Unique identifier for the role. |
| `role_name` | VARCHAR(50) | NOT NULL, UNIQUE | Name of the role (e.g., Admin, Doctor, Receptionist). |
| `description` | VARCHAR(255) | | Description of the role's permissions. |

### 3.2 `users`
Stores login accounts for all system users.

| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `user_id` | INT | PRIMARY KEY, AUTO_INCREMENT | Unique identifier for the user. |
| `username` | VARCHAR(50) | NOT NULL, UNIQUE | Login username. |
| `password_hash` | VARCHAR(255) | NOT NULL | Hashed password (using bcrypt). |
| `role_id` | INT | FOREIGN KEY (`roles.role_id`) | Links to the user's role. |
| `status` | VARCHAR(20) | DEFAULT 'Active' | Account status (Active, Inactive). |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation time. |
| `updated_at` | TIMESTAMP | ON UPDATE CURRENT_TIMESTAMP | Last update time. |

### 3.3 `departments`
Stores the list of hospital departments.

| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `department_id` | INT | PRIMARY KEY, AUTO_INCREMENT | Unique identifier for the department. |
| `department_name` | VARCHAR(100) | NOT NULL, UNIQUE | Name of the department (e.g., Cardiology, Neurology). |
| `description` | TEXT | | Brief description of the department. |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation time. |

### 3.4 `doctors`
Stores doctor details and schedules.

| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `doctor_id` | INT | PRIMARY KEY, AUTO_INCREMENT | Unique identifier for the doctor. |
| `user_id` | INT | FOREIGN KEY (`users.user_id`) | Links to the doctor's login account. |
| `department_id` | INT | FOREIGN KEY (`departments.department_id`) | Primary department assignment. |
| `full_name` | VARCHAR(100) | NOT NULL | Doctor's full name. |
| `specialization` | VARCHAR(100) | | Doctor's specific specialization. |
| `contact_number` | VARCHAR(20) | | Doctor's contact number. |
| `email` | VARCHAR(100) | UNIQUE | Doctor's email address. |
| `working_hours_start` | TIME | | Start of working hours. |
| `working_hours_end` | TIME | | End of working hours. |
| `lunch_break_start` | TIME | | Start of lunch break. |
| `lunch_break_end` | TIME | | End of lunch break. |
| `max_appointments_per_day` | INT | | Maximum allowed appointments per day. |
| `status` | VARCHAR(20) | DEFAULT 'Active' | Employment status. |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation time. |

### 3.5 `patients`
Stores patient details and contact information.

| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `patient_id` | VARCHAR(20) | PRIMARY KEY | Auto-generated unique patient ID. |
| `full_name` | VARCHAR(100) | NOT NULL | Patient's full name. |
| `date_of_birth` | DATE | | Patient's date of birth. |
| `gender` | VARCHAR(10) | | Patient's gender. |
| `contact_number` | VARCHAR(20) | NOT NULL | Patient's primary contact number. |
| `email` | VARCHAR(100) | | Patient's email address. |
| `address` | TEXT | | Patient's physical address. |
| `emergency_contact_name` | VARCHAR(100) | | Name of emergency contact. |
| `emergency_contact_number` | VARCHAR(20) | | Phone number of emergency contact. |
| `registered_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Registration timestamp. |

### 3.6 `appointments`
Stores appointment details and schedules.

| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `appointment_id` | INT | PRIMARY KEY, AUTO_INCREMENT | Unique identifier for the appointment. |
| `patient_id` | VARCHAR(20) | FOREIGN KEY (`patients.patient_id`) | Patient associated with the appointment. |
| `doctor_id` | INT | FOREIGN KEY (`doctors.doctor_id`) | Doctor associated with the appointment. |
| `appointment_date` | DATE | NOT NULL | Date of the appointment. |
| `start_time` | TIME | NOT NULL | Start time of the appointment slot. |
| `end_time` | TIME | NOT NULL | End time of the appointment slot. |
| `status` | VARCHAR(20) | DEFAULT 'Booked' | Appointment status (Booked, Completed, Cancelled, No Show). |
| `notes` | TEXT | | Optional notes added during booking. |
| `created_by` | INT | FOREIGN KEY (`users.user_id`) | User who booked the appointment. |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Booking timestamp. |

### 3.7 `medical_history`
Stores patient's previous illnesses and medical history.

| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `history_id` | INT | PRIMARY KEY, AUTO_INCREMENT | Unique identifier for the history record. |
| `patient_id` | VARCHAR(20) | FOREIGN KEY (`patients.patient_id`) | Patient associated with the history. |
| `condition` | VARCHAR(255) | NOT NULL | Name of the medical condition. |
| `description` | TEXT | | Details about the condition. |
| `diagnosed_date` | DATE | | Date the condition was diagnosed. |
| `status` | VARCHAR(20) | DEFAULT 'Active' | Status of the condition (Active, Resolved). |

### 3.8 `visit_records`
Stores every consultation/visit a patient has with a doctor.

| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `visit_id` | INT | PRIMARY KEY, AUTO_INCREMENT | Unique identifier for the visit. |
| `appointment_id` | INT | FOREIGN KEY (`appointments.appointment_id`) | Links to the specific appointment. |
| `doctor_id` | INT | FOREIGN KEY (`doctors.doctor_id`) | Doctor who conducted the visit. |
| `visit_date` | DATE | NOT NULL | Date of the visit. |
| `symptoms` | TEXT | | Patient's reported symptoms. |
| `diagnosis` | TEXT | | Doctor's diagnosis. |
| `doctor_notes` | TEXT | | Additional notes by the doctor. |
| `follow_up_date` | DATE | | Recommended date for follow-up. |
| `status` | VARCHAR(20) | DEFAULT 'Completed' | Status of the visit record. |

### 3.9 `prescriptions`
Stores medicines prescribed during a visit.

| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `prescription_id` | INT | PRIMARY KEY, AUTO_INCREMENT | Unique identifier for the prescription. |
| `visit_id` | INT | FOREIGN KEY (`visit_records.visit_id`) | Links to the specific visit. |
| `medicine_name` | VARCHAR(100) | NOT NULL | Name of the prescribed medicine. |
| `dosage` | VARCHAR(50) | | Dosage instructions (e.g., 500mg). |
| `frequency` | VARCHAR(50) | | Frequency of intake (e.g., twice daily). |
| `duration` | VARCHAR(50) | | Duration of the course (e.g., 7 days). |
| `instructions` | TEXT | | Special instructions for the patient. |

### 3.10 `test_reports`
Stores uploaded test reports for a specific visit.

| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `report_id` | INT | PRIMARY KEY, AUTO_INCREMENT | Unique identifier for the report. |
| `visit_id` | INT | FOREIGN KEY (`visit_records.visit_id`) | Links to the specific visit. |
| `report_name` | VARCHAR(100) | NOT NULL | Name or type of the test report. |
| `file_path` | VARCHAR(255) | NOT NULL | Local path to the uploaded report file. |
| `upload_date` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Date and time of upload. |

### 3.11 `audit_logs`
Tracks user activity for security and compliance.

| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `log_id` | INT | PRIMARY KEY, AUTO_INCREMENT | Unique identifier for the log entry. |
| `user_id` | INT | FOREIGN KEY (`users.user_id`) | User who performed the action. |
| `action` | VARCHAR(100) | NOT NULL | Description of the action (e.g., 'Login', 'Book Appointment'). |
| `target_entity` | VARCHAR(50) | | Entity affected (e.g., 'Patient', 'Appointment'). |
| `target_id` | VARCHAR(50) | | ID of the affected entity. |
| `ip_address` | VARCHAR(45) | | IP address of the user (if applicable). |
| `timestamp` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Time the action occurred. |

## 4. Indexing Strategy

To ensure optimal performance for search and retrieval operations, the following indexes should be implemented:

* **`patients`:** Index on `contact_number` (for quick patient search).
* **`appointments`:** Composite index on `appointment_date` and `doctor_id` (for generating doctor schedules).
* **`appointments`:** Index on `patient_id` (for retrieving patient appointment history).
* **`users`:** Index on `username` (for quick login lookups).
* **`audit_logs`:** Index on `timestamp` (for generating activity reports).

## 5. Security Considerations

* **Password Storage:** The `password_hash` column in the `users` table must store the output of the `bcrypt` hashing algorithm. Plain-text passwords must never be stored.
* **Data Integrity:** Foreign key constraints with `ON DELETE RESTRICT` or `ON DELETE CASCADE` (where appropriate) must be enforced to maintain data integrity across related tables.
* **Parameterized Queries:** All interactions with the database must use parameterized queries to prevent SQL injection vulnerabilities.
