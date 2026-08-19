-- ============================================================================
-- Hospital Scheduling System – Database Schema
-- Engine   : MySQL 8.0+
-- Charset  : utf8mb4 / utf8mb4_unicode_ci
-- Normal Form : Third Normal Form (3NF)
--
-- Every non-key column depends on "the key, the whole key, and nothing but
-- the key."  Derived/calculated values are never stored.
-- ============================================================================

CREATE DATABASE IF NOT EXISTS `hospital_db`
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE `hospital_db`;

-- -------------------------------------------------------------------------
-- 1. roles – System access roles (Admin, Doctor, Receptionist)
-- -------------------------------------------------------------------------
CREATE TABLE `roles` (
    `role_id`       INT           NOT NULL AUTO_INCREMENT,
    `role_name`     VARCHAR(50)   NOT NULL,
    `description`   VARCHAR(255)  DEFAULT NULL,
    `created_at`    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (`role_id`),
    UNIQUE KEY `uk_roles_name` (`role_name`)
) ENGINE=InnoDB;

-- -------------------------------------------------------------------------
-- 2. users – Login accounts for all system users
-- -------------------------------------------------------------------------
CREATE TABLE `users` (
    `user_id`               INT           NOT NULL AUTO_INCREMENT,
    `username`              VARCHAR(50)   NOT NULL,
    `password_hash`         VARCHAR(255)  NOT NULL,
    `role_id`               INT           NOT NULL,
    `status`                VARCHAR(20)   NOT NULL DEFAULT 'Active',
    `full_name`             VARCHAR(100)  DEFAULT NULL,
    `email`                 VARCHAR(100)  DEFAULT NULL,
    `last_login`            TIMESTAMP     NULL DEFAULT NULL,
    `failed_login_attempts` INT           NOT NULL DEFAULT 0,
    `locked_until`          TIMESTAMP     NULL DEFAULT NULL,
    `created_at`            TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`            TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (`user_id`),
    UNIQUE KEY `uk_users_username` (`username`),
    UNIQUE KEY `uk_users_email` (`email`),
    KEY `idx_users_role_id` (`role_id`),
    KEY `idx_users_status` (`status`),

    CONSTRAINT `fk_users_role` FOREIGN KEY (`role_id`)
        REFERENCES `roles` (`role_id`) ON DELETE RESTRICT ON UPDATE CASCADE,

    CONSTRAINT `ck_users_status` CHECK (`status` IN ('Active', 'Inactive'))
) ENGINE=InnoDB;

-- -------------------------------------------------------------------------
-- 3. departments – Hospital departments / speciality units
-- -------------------------------------------------------------------------
CREATE TABLE `departments` (
    `department_id`   INT           NOT NULL AUTO_INCREMENT,
    `department_name` VARCHAR(100)  NOT NULL,
    `description`     TEXT          DEFAULT NULL,
    `created_at`      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (`department_id`),
    UNIQUE KEY `uk_departments_name` (`department_name`)
) ENGINE=InnoDB;

-- -------------------------------------------------------------------------
-- 4. doctors – Medical practitioners (profile data only; schedule is separate)
--
-- NOTE: Working hours have been removed from this table.  Daily schedules
--       live in `doctor_schedules`.  Lunch-break info also moved there so
--       that a doctor can have different breaks on different days.
-- -------------------------------------------------------------------------
CREATE TABLE `doctors` (
    `doctor_id`              INT             NOT NULL AUTO_INCREMENT,
    `user_id`                INT             NOT NULL,
    `department_id`          INT             NOT NULL,
    `full_name`              VARCHAR(100)    NOT NULL,
    `specialization`         VARCHAR(100)    DEFAULT NULL,
    `contact_number`         VARCHAR(20)     DEFAULT NULL,
    `email`                  VARCHAR(100)    DEFAULT NULL,
    `qualification`          VARCHAR(200)    DEFAULT NULL,
    `license_number`         VARCHAR(50)     DEFAULT NULL COMMENT 'Professional licence / registration',
    `experience_years`       INT             NOT NULL DEFAULT 0,
    `consultation_fee`       DECIMAL(10,2)   NOT NULL DEFAULT 0.00,
    `max_appointments_per_day` INT           NOT NULL DEFAULT 20,
    `status`                 VARCHAR(20)     NOT NULL DEFAULT 'Active',
    `created_at`             TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`             TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (`doctor_id`),
    UNIQUE KEY `uk_doctors_user` (`user_id`),
    UNIQUE KEY `uk_doctors_email` (`email`),
    KEY `idx_doctors_department` (`department_id`),
    KEY `idx_doctors_status` (`status`),

    CONSTRAINT `fk_doctors_user` FOREIGN KEY (`user_id`)
        REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_doctors_department` FOREIGN KEY (`department_id`)
        REFERENCES `departments` (`department_id`) ON DELETE RESTRICT ON UPDATE CASCADE,

    CONSTRAINT `ck_doctors_status` CHECK (`status` IN ('Active', 'Inactive', 'On Leave')),
    CONSTRAINT `ck_doctors_experience` CHECK (`experience_years` BETWEEN 0 AND 70),
    CONSTRAINT `ck_doctors_fee` CHECK (`consultation_fee` >= 0),
    CONSTRAINT `ck_doctors_max_appts` CHECK (`max_appointments_per_day` BETWEEN 1 AND 100)
) ENGINE=InnoDB;

-- -------------------------------------------------------------------------
-- 5. doctor_schedules – Recurring weekly schedule per doctor
--
-- Stores one row per day-of-week that a doctor works.
-- Lunch break is defined per-day so it can vary (e.g. different hours on
-- Wednesday vs. Monday).
-- -------------------------------------------------------------------------
CREATE TABLE `doctor_schedules` (
    `schedule_id`     INT         NOT NULL AUTO_INCREMENT,
    `doctor_id`       INT         NOT NULL,
    `day_of_week`     TINYINT     NOT NULL COMMENT '0=Sunday … 6=Saturday',
    `start_time`      TIME        NOT NULL,
    `end_time`        TIME        NOT NULL,
    `lunch_break_start` TIME      DEFAULT NULL,
    `lunch_break_end`   TIME      DEFAULT NULL,
    `is_available`    BOOLEAN     NOT NULL DEFAULT TRUE,
    `slot_duration`   INT         NOT NULL DEFAULT 15 COMMENT 'Minutes per appointment slot',
    `created_at`      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (`schedule_id`),
    UNIQUE KEY `uk_schedule_doctor_day` (`doctor_id`, `day_of_week`),

    CONSTRAINT `fk_schedules_doctor` FOREIGN KEY (`doctor_id`)
        REFERENCES `doctors` (`doctor_id`) ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT `ck_schedules_day` CHECK (`day_of_week` BETWEEN 0 AND 6),
    CONSTRAINT `ck_schedules_times` CHECK (`start_time` < `end_time`),
    CONSTRAINT `ck_schedules_lunch` CHECK (
        (`lunch_break_start` IS NULL AND `lunch_break_end` IS NULL)
        OR
        (`lunch_break_start` IS NOT NULL
         AND `lunch_break_end` IS NOT NULL
         AND `lunch_break_start` < `lunch_break_end`)
    ),
    CONSTRAINT `ck_schedules_slot` CHECK (`slot_duration` BETWEEN 5 AND 120)
) ENGINE=InnoDB;

-- -------------------------------------------------------------------------
-- 6. doctor_leave – Non-recurring leave / time-off records
-- -------------------------------------------------------------------------
CREATE TABLE `doctor_leave` (
    `leave_id`          INT           NOT NULL AUTO_INCREMENT,
    `doctor_id`         INT           NOT NULL,
    `leave_start_date`  DATE          NOT NULL,
    `leave_end_date`    DATE          NOT NULL,
    `reason`            VARCHAR(255)  DEFAULT NULL,
    `status`            VARCHAR(20)   NOT NULL DEFAULT 'Approved',
    `created_at`        TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (`leave_id`),
    KEY `idx_leave_doctor` (`doctor_id`),
    KEY `idx_leave_dates` (`leave_start_date`, `leave_end_date`),

    CONSTRAINT `fk_leave_doctor` FOREIGN KEY (`doctor_id`)
        REFERENCES `doctors` (`doctor_id`) ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT `ck_leave_dates` CHECK (`leave_start_date` <= `leave_end_date`),
    CONSTRAINT `ck_leave_status` CHECK (`status` IN ('Approved', 'Pending', 'Rejected'))
) ENGINE=InnoDB;

-- -------------------------------------------------------------------------
-- 7. patients – Patient registration and contact data
--
-- Primary key is application-generated (PAT-NNNNN).  This is a deliberate
-- business choice so the ID is human-readable; a surrogate INT auto_increment
-- would be more efficient but less user-friendly.
-- -------------------------------------------------------------------------
CREATE TABLE `patients` (
    `patient_id`               VARCHAR(20)   NOT NULL,
    `full_name`                VARCHAR(100)  NOT NULL,
    `date_of_birth`            DATE          DEFAULT NULL,
    `gender`                   VARCHAR(10)   DEFAULT NULL,
    `contact_number`           VARCHAR(20)   NOT NULL,
    `email`                    VARCHAR(100)  DEFAULT NULL,
    `address`                  TEXT          DEFAULT NULL,
    `emergency_contact_name`   VARCHAR(100)  DEFAULT NULL,
    `emergency_contact_number` VARCHAR(20)   DEFAULT NULL,
    `blood_group`              VARCHAR(5)    DEFAULT NULL,
    `allergies`                TEXT          DEFAULT NULL,
    `registered_at`            TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`               TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (`patient_id`),
    KEY `idx_patients_name` (`full_name`),
    KEY `idx_patients_contact` (`contact_number`),
    KEY `idx_patients_email` (`email`),

    CONSTRAINT `ck_patients_gender` CHECK (`gender` IN ('Male', 'Female', 'Other')),
    CONSTRAINT `ck_patients_blood` CHECK (`blood_group` IN (
        'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'
    ))
) ENGINE=InnoDB;

-- -------------------------------------------------------------------------
-- 8. appointments – Booking of a patient with a doctor at a time slot
--
-- The composite index (doctor_id, appointment_date, start_time) is
-- critical for fast overlap-detection queries.
-- -------------------------------------------------------------------------
CREATE TABLE `appointments` (
    `appointment_id`    INT           NOT NULL AUTO_INCREMENT,
    `patient_id`        VARCHAR(20)   NOT NULL,
    `doctor_id`         INT           NOT NULL,
    `appointment_date`  DATE          NOT NULL,
    `start_time`        TIME          NOT NULL,
    `end_time`          TIME          NOT NULL,
    `status`            VARCHAR(20)   NOT NULL DEFAULT 'Booked',
    `notes`             TEXT          DEFAULT NULL,
    `created_by`        INT           NOT NULL COMMENT 'User who booked this appointment',
    `created_at`        TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`        TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `rescheduled_from_id` INT        DEFAULT NULL COMMENT 'When set, this row is a reschedule of the referenced appointment',
    -- DB-level double-booking backstop: one live (non-cancelled /
    -- non-no-show) booking per (doctor_id, appointment_date, start_time).
    -- NULL for Cancelled/No Show rows so the slot can be re-booked.
    `booking_key`       VARCHAR(64)   GENERATED ALWAYS AS (
        IF(`status` IN ('Cancelled', 'No Show'), NULL,
           CONCAT_WS('|', `doctor_id`, `appointment_date`, `start_time`))
    ) STORED,

    PRIMARY KEY (`appointment_id`),
    UNIQUE KEY `uk_appt_booking_key` (`booking_key`),
    KEY `idx_appt_doctor_date_time` (`doctor_id`, `appointment_date`, `start_time`),
    KEY `idx_appt_patient` (`patient_id`),
    KEY `idx_appt_date` (`appointment_date`),
    KEY `idx_appt_status` (`status`),
    KEY `idx_appt_rescheduled_from` (`rescheduled_from_id`),

    CONSTRAINT `fk_appt_patient` FOREIGN KEY (`patient_id`)
        REFERENCES `patients` (`patient_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `fk_appt_doctor` FOREIGN KEY (`doctor_id`)
        REFERENCES `doctors` (`doctor_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `fk_appt_created_by` FOREIGN KEY (`created_by`)
        REFERENCES `users` (`user_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `fk_appt_rescheduled_from` FOREIGN KEY (`rescheduled_from_id`)
        REFERENCES `appointments` (`appointment_id`) ON DELETE SET NULL ON UPDATE CASCADE,

    CONSTRAINT `ck_appt_times` CHECK (`start_time` < `end_time`),
    CONSTRAINT `ck_appt_status` CHECK (`status` IN (
        'Booked', 'Completed', 'Cancelled', 'No Show'
    ))
) ENGINE=InnoDB;

-- -------------------------------------------------------------------------
-- 9. medical_history – Patient long-term medical conditions
-- -------------------------------------------------------------------------
CREATE TABLE `medical_history` (
    `history_id`     INT           NOT NULL AUTO_INCREMENT,
    `patient_id`     VARCHAR(20)   NOT NULL,
    `condition_name` VARCHAR(255)  NOT NULL,
    `description`    TEXT          DEFAULT NULL,
    `diagnosed_date` DATE          DEFAULT NULL,
    `status`         VARCHAR(20)   NOT NULL DEFAULT 'Active',
    `created_at`     TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`     TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (`history_id`),
    KEY `idx_medhist_patient` (`patient_id`),

    CONSTRAINT `fk_medhist_patient` FOREIGN KEY (`patient_id`)
        REFERENCES `patients` (`patient_id`) ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT `ck_medhist_status` CHECK (`status` IN ('Active', 'Resolved', 'Chronic'))
) ENGINE=InnoDB;

-- -------------------------------------------------------------------------
-- 10. visit_records – Clinical encounter tied to an appointment
--
-- patient_id is NOT stored here; it is reachable through
-- appointments.patient_id.  This preserves 3NF.
-- -------------------------------------------------------------------------
CREATE TABLE `visit_records` (
    `visit_id`       INT           NOT NULL AUTO_INCREMENT,
    `appointment_id` INT           NOT NULL,
    `doctor_id`      INT           NOT NULL,
    `visit_date`     DATE          NOT NULL,
    `symptoms`       TEXT          DEFAULT NULL,
    `diagnosis`      TEXT          DEFAULT NULL,
    `doctor_notes`   TEXT          DEFAULT NULL,
    `follow_up_date` DATE          DEFAULT NULL,
    `status`         VARCHAR(20)   NOT NULL DEFAULT 'Completed',
    `created_at`     TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`     TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (`visit_id`),
    UNIQUE KEY `uk_visit_appointment` (`appointment_id`),
    KEY `idx_visit_doctor` (`doctor_id`),
    KEY `idx_visit_date` (`visit_date`),

    CONSTRAINT `fk_visit_appointment` FOREIGN KEY (`appointment_id`)
        REFERENCES `appointments` (`appointment_id`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_visit_doctor` FOREIGN KEY (`doctor_id`)
        REFERENCES `doctors` (`doctor_id`) ON DELETE RESTRICT ON UPDATE CASCADE,

    CONSTRAINT `ck_visit_status` CHECK (`status` IN ('Completed', 'In Progress', 'Cancelled'))
) ENGINE=InnoDB;

-- -------------------------------------------------------------------------
-- 11. prescriptions – Medications prescribed during a visit
-- -------------------------------------------------------------------------
CREATE TABLE `prescriptions` (
    `prescription_id` INT           NOT NULL AUTO_INCREMENT,
    `visit_id`        INT           NOT NULL,
    `medicine_name`   VARCHAR(100)  NOT NULL,
    `dosage`          VARCHAR(50)   DEFAULT NULL COMMENT 'e.g. 500mg',
    `frequency`       VARCHAR(50)   DEFAULT NULL COMMENT 'e.g. Twice daily',
    `duration`        VARCHAR(50)   DEFAULT NULL COMMENT 'e.g. 7 days',
    `route`           VARCHAR(50)   DEFAULT NULL COMMENT 'Oral / IV / Topical / etc.',
    `instructions`    TEXT          DEFAULT NULL,

    PRIMARY KEY (`prescription_id`),
    KEY `idx_rx_visit` (`visit_id`),

    CONSTRAINT `fk_rx_visit` FOREIGN KEY (`visit_id`)
        REFERENCES `visit_records` (`visit_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- -------------------------------------------------------------------------
-- 12. test_reports – Uploaded diagnostic reports attached to a visit
-- -------------------------------------------------------------------------
CREATE TABLE `test_reports` (
    `report_id`   INT           NOT NULL AUTO_INCREMENT,
    `visit_id`    INT           NOT NULL,
    `report_name` VARCHAR(100)  NOT NULL,
    `file_path`   VARCHAR(255)  NOT NULL,
    `file_type`   VARCHAR(50)   DEFAULT NULL,
    `file_size`   INT           DEFAULT NULL COMMENT 'Size in bytes',
    `upload_date` TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (`report_id`),
    KEY `idx_reports_visit` (`visit_id`),

    CONSTRAINT `fk_reports_visit` FOREIGN KEY (`visit_id`)
        REFERENCES `visit_records` (`visit_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- -------------------------------------------------------------------------
-- 13. patient_documents – General documents attached to a patient record
-- -------------------------------------------------------------------------
CREATE TABLE `patient_documents` (
    `document_id`   INT           NOT NULL AUTO_INCREMENT,
    `patient_id`    VARCHAR(20)   NOT NULL,
    `document_name` VARCHAR(100)  NOT NULL,
    `file_path`     VARCHAR(255)  NOT NULL,
    `file_type`     VARCHAR(50)   DEFAULT NULL,
    `file_size`     INT           DEFAULT NULL,
    `uploaded_by`   INT           DEFAULT NULL,
    `upload_date`   TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (`document_id`),
    KEY `idx_docs_patient` (`patient_id`),

    CONSTRAINT `fk_docs_patient` FOREIGN KEY (`patient_id`)
        REFERENCES `patients` (`patient_id`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_docs_uploader` FOREIGN KEY (`uploaded_by`)
        REFERENCES `users` (`user_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB;

-- -------------------------------------------------------------------------
-- Application settings – key/value preferences (e.g. UI theme)
-- -------------------------------------------------------------------------
CREATE TABLE `app_settings` (
    `setting_key`   VARCHAR(100)  NOT NULL,
    `setting_value` TEXT,
    `updated_at`    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (`setting_key`)
) ENGINE=InnoDB;

-- -------------------------------------------------------------------------
-- 14. hospital_holidays – Dates the hospital is closed
-- -------------------------------------------------------------------------
CREATE TABLE `hospital_holidays` (
    `holiday_id`   INT           NOT NULL AUTO_INCREMENT,
    `holiday_date` DATE          NOT NULL,
    `holiday_name` VARCHAR(100)  NOT NULL,
    `description`  TEXT          DEFAULT NULL,
    `is_recurring` BOOLEAN       NOT NULL DEFAULT FALSE,
    `created_at`   TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (`holiday_id`),
    UNIQUE KEY `uk_holidays_date` (`holiday_date`),
    KEY `idx_holidays_date` (`holiday_date`)
) ENGINE=InnoDB;

-- -------------------------------------------------------------------------
-- 15. audit_logs – Immutable trail of user actions
-- -------------------------------------------------------------------------
CREATE TABLE `audit_logs` (
    `log_id`         INT           NOT NULL AUTO_INCREMENT,
    `user_id`        INT           DEFAULT NULL,
    `action`         VARCHAR(100)  NOT NULL,
    `target_entity`  VARCHAR(50)   DEFAULT NULL,
    `target_id`      VARCHAR(50)   DEFAULT NULL,
    `old_values`     JSON          DEFAULT NULL,
    `new_values`     JSON          DEFAULT NULL,
    `ip_address`     VARCHAR(45)   DEFAULT NULL,
    `user_agent`     TEXT          DEFAULT NULL,
    `timestamp`      TIMESTAMP(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `previous_hash`  CHAR(64)      DEFAULT NULL,
    `row_hash`       CHAR(64)      NOT NULL,

    PRIMARY KEY (`log_id`),
    KEY `idx_audit_user` (`user_id`),
    KEY `idx_audit_time` (`timestamp`),
    KEY `idx_audit_action` (`action`),
    KEY `idx_audit_entity` (`target_entity`, `target_id`),
    UNIQUE KEY `uk_audit_row_hash` (`row_hash`),

    CONSTRAINT `fk_audit_user` FOREIGN KEY (`user_id`)
        REFERENCES `users` (`user_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB;
