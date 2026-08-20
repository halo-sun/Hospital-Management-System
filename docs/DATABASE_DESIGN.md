# Database Design Documentation

## Hospital Scheduling System

---

## 1. Overview

The database is a **MySQL 8.0+** relational database designed in **Third Normal Form (3NF)** for a hospital patient and appointment management desktop application. It stores all persistent data including user accounts, patient registrations, doctor schedules, appointments, clinical records, and audit logs.

**Character set:** `utf8mb4` with `utf8mb4_unicode_ci` collation for full Unicode support including emoji and international characters.

**Engine:** All tables use `InnoDB` for ACID compliance, foreign key support, and row-level locking.

---

## 2. Entity-Relationship Diagram (Textual)

```
roles (1) ──< users (1) ──< doctors (1) ──< doctor_schedules
             │                │
             │                ├──< doctor_leave
             │                │
             │                └──< appointments >── patients
             │                       │
             │                       └──< visit_records
             │                              │
             │                              ├──< prescriptions
             │                              └──< test_reports
             │
             ├──< patient_documents >── patients
             │
             └──< audit_logs

departments (1) ──< doctors

hospital_holidays (standalone reference table)
```

**Legend:** `(1)` = one side, `─<` = zero-or-many side, `>──` = many-to-one

---

## 3. Table Definitions & 3NF Justification

### 3.1 `roles` (Reference/Lookup)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `role_id` | INT | PK, AUTO_INCREMENT | Surrogate key |
| `role_name` | VARCHAR(50) | NOT NULL, UNIQUE | `Admin`, `Doctor`, `Receptionist` |
| `description` | VARCHAR(255) | NULL | Human-readable purpose |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Row creation time |

**3NF:** ✅ Atomic values, no transitive dependencies.

---

### 3.2 `users` (Strong Entity)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `user_id` | INT | PK, AUTO_INCREMENT | Surrogate key |
| `username` | VARCHAR(50) | NOT NULL, UNIQUE | Login identifier |
| `password_hash` | VARCHAR(255) | NOT NULL | bcrypt hash |
| `role_id` | INT | FK → roles | User's role |
| `status` | VARCHAR(20) | CHECK (`Active`, `Inactive`) | Account state |
| `full_name` | VARCHAR(100) | NULL | Display name |
| `email` | VARCHAR(100) | UNIQUE, NULL | Contact email |
| `last_login` | TIMESTAMP | NULL | Last successful login |
| `failed_login_attempts` | INT | DEFAULT 0 | Brute-force tracking |
| `locked_until` | TIMESTAMP | NULL | Account lock expiry |
| `created_at` | TIMESTAMP | DEFAULT NOW() | |
| `updated_at` | TIMESTAMP | ON UPDATE NOW() | |

**3NF:** ✅ All non-key columns depend on `user_id`. `role_name` is not stored here; it's reached through the FK to `roles` (Boyce-Codd compliance).

**Cascade:** `ON DELETE RESTRICT` — cannot delete a role that has users.

---

### 3.3 `departments`

| Column | Type | Constraints |
|--------|------|-------------|
| `department_id` | INT | PK, AUTO_INCREMENT |
| `department_name` | VARCHAR(100) | NOT NULL, UNIQUE |
| `description` | TEXT | NULL |
| `created_at` / `updated_at` | TIMESTAMP | Standard audit columns |

**3NF:** ✅ Simple entity, no dependencies.

---

### 3.4 `doctors`

| Column | Type | Constraints |
|--------|------|-------------|
| `doctor_id` | INT | PK, AUTO_INCREMENT |
| `user_id` | INT | FK → users, UNIQUE, NOT NULL |
| `department_id` | INT | FK → departments, NOT NULL |
| `full_name` | VARCHAR(100) | NOT NULL |
| `specialization` | VARCHAR(100) | NULL |
| `contact_number` | VARCHAR(20) | NULL |
| `email` | VARCHAR(100) | UNIQUE, NULL |
| `qualification` | VARCHAR(200) | NULL |
| `license_number` | VARCHAR(50) | NULL (professional registration) |
| `experience_years` | INT | DEFAULT 0, CHECK (0–70) |
| `consultation_fee` | DECIMAL(10,2) | DEFAULT 0, CHECK (≥ 0) |
| `max_appointments_per_day` | INT | DEFAULT 20, CHECK (1–100) |
| `status` | VARCHAR(20) | CHECK (`Active`, `Inactive`, `On Leave`) |

**3NF:** ✅ Doctor-specific attributes depend on `doctor_id`. Working hours and lunch breaks have been **removed** from this table (they were partial-key dependencies on `day_of_week`). They now live in `doctor_schedules` where they belong.

**Cascade:** `ON DELETE CASCADE` from users (doctor → user), `ON DELETE RESTRICT` from departments (can't delete a department with doctors).

---

### 3.5 `doctor_schedules`

**Normalization note:** This table was designed to remove the multi-valued dependency that existed when working hours were stored in `doctors`. A doctor works many days; each day has its own schedule.

| Column | Type | Constraints |
|--------|------|-------------|
| `schedule_id` | INT | PK, AUTO_INCREMENT |
| `doctor_id` | INT | FK → doctors, NOT NULL |
| `day_of_week` | TINYINT | CHECK (0–6), NOT NULL |
| `start_time` | TIME | NOT NULL |
| `end_time` | TIME | NOT NULL, CHECK (start < end) |
| `lunch_break_start` | TIME | NULL |
| `lunch_break_end` | TIME | NULL, CHECK (lunch_start < lunch_end) |
| `is_available` | BOOLEAN | DEFAULT TRUE |
| `slot_duration` | INT | DEFAULT 15 minutes, CHECK (5–120) |

**Unique constraint:** `(doctor_id, day_of_week)` — one schedule per doctor per day.

**3NF:** ✅ The composite primary key would be `(doctor_id, day_of_week)`, but a surrogate `schedule_id` is used for simpler JOINs. All columns are fully functionally dependent on `(doctor_id, day_of_week)`.

**Cascade:** `ON DELETE CASCADE` — deleting a doctor removes their schedules.

---

### 3.6 `doctor_leave`

Stores date ranges when a doctor is unavailable.

| Column | Type | Constraints |
|--------|------|-------------|
| `leave_id` | INT | PK |
| `doctor_id` | INT | FK → doctors |
| `leave_start_date` | DATE | NOT NULL |
| `leave_end_date` | DATE | NOT NULL, CHECK (start ≤ end) |
| `reason` | VARCHAR(255) | NULL |
| `status` | VARCHAR(20) | CHECK (`Approved`, `Pending`, `Rejected`) |

**3NF:** ✅ All columns depend on `leave_id`.

**Cascade:** `ON DELETE CASCADE` — doctor deletion cascades to leaves.

---

### 3.7 `patients`

**Design choice:** The primary key is an application-generated VARCHAR (`PAT-00001`) rather than an INT AUTO_INCREMENT. This provides human-readable IDs on forms and reports. The trade-off is slightly larger index size, which is acceptable for the expected data volume.

| Column | Type | Constraints |
|--------|------|-------------|
| `patient_id` | VARCHAR(20) | PK (application-generated) |
| `full_name` | VARCHAR(100) | NOT NULL |
| `date_of_birth` | DATE | NULL |
| `gender` | VARCHAR(10) | CHECK (`Male`, `Female`, `Other`), NULL |
| `contact_number` | VARCHAR(20) | NOT NULL |
| `email` | VARCHAR(100) | NULL |
| `address` | TEXT | NULL |
| `emergency_contact_name` | VARCHAR(100) | NULL |
| `emergency_contact_number` | VARCHAR(20) | NULL |
| `blood_group` | VARCHAR(5) | CHECK (valid types), NULL |
| `allergies` | TEXT | NULL |

**3NF:** ✅ All columns depend on `patient_id`. Emergency contact details are kept in this table (not a separate table) because they are 1:1 with the patient.

---

### 3.8 `appointments`

The core bridging table connecting patients and doctors at a specific time.

| Column | Type | Constraints |
|--------|------|-------------|
| `appointment_id` | INT | PK, AUTO_INCREMENT |
| `patient_id` | VARCHAR(20) | FK → patients |
| `doctor_id` | INT | FK → doctors |
| `appointment_date` | DATE | NOT NULL |
| `start_time` | TIME | NOT NULL |
| `end_time` | TIME | NOT NULL, CHECK (start < end) |
| `status` | VARCHAR(20) | CHECK (`Booked`, `Completed`, `Cancelled`, `No Show`) |
| `notes` | TEXT | NULL |
| `created_by` | INT | FK → users |

**Critical index:** `idx_appt_doctor_date_time (doctor_id, appointment_date, start_time)` — this composite index enables fast overlap-detection queries when booking appointments.

**3NF:** ✅ All columns depend on `appointment_id`. `patient_name`, `doctor_name`, etc. are never stored here; they are reached through FKs.

**Cascade:** `ON DELETE RESTRICT` from patients and doctors — prevents accidental deletion of entities with existing appointments.

---

### 3.9 `medical_history`

Long-term conditions and diagnoses for a patient.

| Column | Type | Constraints |
|--------|------|-------------|
| `history_id` | INT | PK |
| `patient_id` | VARCHAR(20) | FK → patients |
| `condition_name` | VARCHAR(255) | NOT NULL |
| `description` | TEXT | NULL |
| `diagnosed_date` | DATE | NULL |
| `status` | VARCHAR(20) | CHECK (`Active`, `Resolved`, `Chronic`) |

**3NF:** ✅ All columns depend on `history_id`.

**Cascade:** `ON DELETE CASCADE` — patient deletion removes their medical history.

---

### 3.10 `visit_records`

Clinical encounter record for a single appointment.

**Design note:** `patient_id` is **not** stored here. It is reachable through `appointment_id → appointments.patient_id`. This preserves 3NF by eliminating the transitive dependency `visit_id → appointment_id → patient_id`.

| Column | Type | Constraints |
|--------|------|-------------|
| `visit_id` | INT | PK |
| `appointment_id` | INT | FK → appointments, UNIQUE (one visit per appointment) |
| `doctor_id` | INT | FK → doctors |
| `visit_date` | DATE | NOT NULL |
| `symptoms` | TEXT | NULL |
| `diagnosis` | TEXT | NULL |
| `doctor_notes` | TEXT | NULL |
| `follow_up_date` | DATE | NULL |

**3NF:** ✅ All columns depend on `visit_id`. `appointment_id → patient_id` is the transitive path, but `patient_id` itself is not stored here.

**Cascade:** `ON DELETE CASCADE` from appointments — cancelling an appointment cascades to its visit record.

---

### 3.11 `prescriptions`

Medications prescribed during a visit.

| Column | Type | Constraints |
|--------|------|-------------|
| `prescription_id` | INT | PK |
| `visit_id` | INT | FK → visit_records |
| `medicine_name` | VARCHAR(100) | NOT NULL |
| `dosage` | VARCHAR(50) | NULL (e.g., "500mg") |
| `frequency` | VARCHAR(50) | NULL (e.g., "Twice daily") |
| `duration` | VARCHAR(50) | NULL (e.g., "7 days") |
| `route` | VARCHAR(50) | NULL (e.g., "Oral", "IV") |
| `instructions` | TEXT | NULL |

**3NF:** ✅ All columns depend on `prescription_id`.

**Cascade:** `ON DELETE CASCADE` — deleting a visit removes its prescriptions.

---

### 3.12 `test_reports`

Uploaded diagnostic reports.

**3NF:** ✅ Same pattern as prescriptions. Visit deletion cascades.

---

### 3.13 `patient_documents`

General-purpose file attachments (consent forms, insurance, etc.).

**3NF:** ✅ Separate from test reports because they attach to the patient directly rather than to a visit.

---

### 3.13b `app_settings`

Key/value preferences table for application-level settings (currently the UI theme, `flatly` / `darkly`). Added by `migrations/003_app_settings.sql` on existing databases; created automatically on fresh ones.

**3NF:** ✅ Single key/value pair per row.

---

### 3.14 `hospital_holidays`

Reference table for dates the hospital is closed. Used by the scheduling engine.

**3NF:** ✅ Standalone lookup.

---

### 3.15 `audit_logs`

Immutable audit trail. All inserts only (no updates or deletes).

| Column | Type | Description |
|--------|------|-------------|
| `log_id` | INT | PK |
| `user_id` | INT | FK → users, SET NULL on delete |
| `action` | VARCHAR(100) | `Login`, `Appointment Booked`, etc. |
| `target_entity` | VARCHAR(50) | `Appointment`, `Patient`, etc. |
| `target_id` | VARCHAR(50) | ID of the affected record |
| `old_values` | JSON | Previous state (for updates) |
| `new_values` | JSON | New state |
| `ip_address` | VARCHAR(45) | IPv4 or IPv6 |
| `user_agent` | TEXT | Client identification |

**3NF:** ✅ All columns depend on `log_id`.

**Cascade:** `ON DELETE SET NULL` — if a user is deleted, their audit records are preserved (anonymous).

---

## 4. Cascade Rules Summary

| FK | Parent | Child | On Delete | On Update |
|----|--------|-------|-----------|-----------|
| `fk_users_role` | roles | users | RESTRICT | CASCADE |
| `fk_doctors_user` | users | doctors | CASCADE | CASCADE |
| `fk_doctors_department` | departments | doctors | RESTRICT | CASCADE |
| `fk_schedules_doctor` | doctors | doctor_schedules | CASCADE | CASCADE |
| `fk_leave_doctor` | doctors | doctor_leave | CASCADE | CASCADE |
| `fk_appt_patient` | patients | appointments | RESTRICT | CASCADE |
| `fk_appt_doctor` | doctors | appointments | RESTRICT | CASCADE |
| `fk_appt_created_by` | users | appointments | RESTRICT | CASCADE |
| `fk_medhist_patient` | patients | medical_history | CASCADE | CASCADE |
| `fk_visit_appointment` | appointments | visit_records | CASCADE | CASCADE |
| `fk_visit_doctor` | doctors | visit_records | RESTRICT | CASCADE |
| `fk_rx_visit` | visit_records | prescriptions | CASCADE | CASCADE |
| `fk_reports_visit` | visit_records | test_reports | CASCADE | CASCADE |
| `fk_docs_patient` | patients | patient_documents | CASCADE | CASCADE |
| `fk_docs_uploader` | users | patient_documents | SET NULL | CASCADE |
| `fk_audit_user` | users | audit_logs | SET NULL | CASCADE |

**Rationale:**
- **RESTRICT** — Used for critical business entities (appointments, departments) where accidental cascade could cause data loss.
- **CASCADE** — Used for dependent child data (schedules, leaves, prescriptions) where the child has no meaning without the parent.
- **SET NULL** — Used for audit/document trails where historical records must be preserved even after user deletion.

---

## 5. Indexing Strategy

| Table | Index | Type | Purpose |
|-------|-------|------|---------|
| `users` | `(username)` | UNIQUE | Fast login lookup |
| `users` | `(email)` | UNIQUE | Unique email enforcement |
| `users` | `(role_id)` | INDEX | Role-based filtering |
| `doctors` | `(user_id)` | UNIQUE | 1:1 mapping lookup |
| `doctors` | `(department_id)` | INDEX | Department-based queries |
| `doctors` | `(status)` | INDEX | Active doctor filter |
| `doctor_schedules` | `(doctor_id, day_of_week)` | UNIQUE | Day-of-week lookup |
| `doctor_leave` | `(leave_start_date, leave_end_date)` | INDEX | Date-range queries |
| `patients` | `(full_name)` | INDEX | Patient search |
| `patients` | `(contact_number)` | INDEX | Phone lookup |
| `appointments` | `(doctor_id, appointment_date, start_time)` | INDEX | **Slot overlap detection** (critical) |
| `appointments` | `(patient_id)` | INDEX | Patient history |
| `appointments` | `(appointment_date)` | INDEX | Daily schedule |
| `visit_records` | `(appointment_id)` | UNIQUE | One-to-one enforcement |
| `visit_records` | `(visit_date)` | INDEX | Daily visit reports |
| `audit_logs` | `(timestamp)` | INDEX | Activity timeline |
| `audit_logs` | `(action)` | INDEX | Action-type filtering |
| `audit_logs` | `(target_entity, target_id)` | INDEX | Entity history lookup |

---

## 6. Security

- **Password storage:** `password_hash` stores **bcrypt** output (not plaintext).
- **SQL injection:** All application queries use parameterized statements.
- **Audit trail:** Every state-changing action is logged in `audit_logs`.
- **Access control:** Role-based access enforced at the application layer using the `roles` table.

---

## 7. Differences from Previous Schema

| Change | Rationale |
|--------|-----------|
| Removed `working_hours_*` from `doctors` | These were partial-key dependencies on `day_of_week`; moved to `doctor_schedules` |
| Moved `lunch_break_*` to `doctor_schedules` | Lunch breaks can vary by day; removing from `doctors` eliminates NULL storage |
| Added `slot_duration` to `doctor_schedules` | Different doctors may prefer different slot lengths |
| Added `license_number` to `doctors` | Professional registration tracking |
| Added `route` to `prescriptions` | Medication administration route (Oral/IV/Topical) |
| Changed `visit_records` FK to CASCADE | Deleting an appointment should cascade to its visit record |
| Added CHECK constraints on all status fields | MySQL 8.0+ supports CHECK; provides schema-level validation |
| Added composite index `(doctor_id, appointment_date, start_time)` | Critical for O(1) overlap detection during booking |
