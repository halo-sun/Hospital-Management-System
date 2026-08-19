"""Database initialization module."""
import logging
import re
from typing import List

from src.config import db_config
from src.constants import (
    Gender, BloodGroup,
    MedicalStatus, VisitStatus, AppointmentStatus, DoctorStatus,
)

logger = logging.getLogger(__name__)


def _quoted_identifier(identifier: str) -> str:
    """Quote a configuration-supplied SQL identifier after strict validation."""
    if not re.fullmatch(r"[A-Za-z0-9_]+", identifier or ""):
        raise ValueError("Invalid SQL identifier in database configuration.")
    return "`" + identifier + "`"

SCHEMA_SQL = """
-- 1. roles table
CREATE TABLE IF NOT EXISTS `roles` (
    `role_id` INT PRIMARY KEY AUTO_INCREMENT,
    `role_name` VARCHAR(50) NOT NULL UNIQUE,
    `description` VARCHAR(255),
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 2. users table
CREATE TABLE IF NOT EXISTS `users` (
    `user_id` INT PRIMARY KEY AUTO_INCREMENT,
    `username` VARCHAR(50) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `role_id` INT NOT NULL,
    `status` VARCHAR(20) DEFAULT 'Active',
    `last_login` TIMESTAMP NULL,
    `failed_login_attempts` INT DEFAULT 0,
    `locked_until` TIMESTAMP NULL,
    `email` VARCHAR(100) UNIQUE,
    `full_name` VARCHAR(100),
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`role_id`) REFERENCES `roles`(`role_id`) ON DELETE RESTRICT,
    INDEX `idx_username` (`username`),
    INDEX `idx_role_id` (`role_id`),
    INDEX `idx_email` (`email`)
) ENGINE=InnoDB;

-- 3. departments table
CREATE TABLE IF NOT EXISTS `departments` (
    `department_id` INT PRIMARY KEY AUTO_INCREMENT,
    `department_name` VARCHAR(100) NOT NULL UNIQUE,
    `description` TEXT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 4. doctors table
CREATE TABLE IF NOT EXISTS `doctors` (
    `doctor_id` INT PRIMARY KEY AUTO_INCREMENT,
    `user_id` INT NOT NULL UNIQUE,
    `department_id` INT NOT NULL,
    `full_name` VARCHAR(100) NOT NULL,
    `specialization` VARCHAR(100),
    `contact_number` VARCHAR(20),
    `email` VARCHAR(100) UNIQUE,
    `qualification` VARCHAR(200),
    `experience_years` INT DEFAULT 0,
    `working_hours_start` TIME,
    `working_hours_end` TIME,
    `lunch_break_start` TIME,
    `lunch_break_end` TIME,
    `max_appointments_per_day` INT DEFAULT 20,
    `consultation_fee` DECIMAL(10,2) DEFAULT 0.00,
    `status` VARCHAR(20) DEFAULT 'Active',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`user_id`) ON DELETE CASCADE,
    FOREIGN KEY (`department_id`) REFERENCES `departments`(`department_id`) ON DELETE RESTRICT,
    INDEX `idx_department_id` (`department_id`),
    INDEX `idx_status` (`status`),
    INDEX `idx_user_id` (`user_id`)
) ENGINE=InnoDB;

-- 5. patients table
CREATE TABLE IF NOT EXISTS `patients` (
    `patient_id` VARCHAR(20) PRIMARY KEY,
    `full_name` VARCHAR(100) NOT NULL,
    `date_of_birth` DATE,
    `gender` VARCHAR(10),
    `contact_number` VARCHAR(20) NOT NULL,
    `email` VARCHAR(100),
    `address` TEXT,
    `emergency_contact_name` VARCHAR(100),
    `emergency_contact_number` VARCHAR(20),
    `blood_group` VARCHAR(5),
    `allergies` TEXT,
    `registered_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_contact_number` (`contact_number`),
    INDEX `idx_full_name` (`full_name`),
    INDEX `idx_email` (`email`)
) ENGINE=InnoDB;

-- 6. appointments table
CREATE TABLE IF NOT EXISTS `appointments` (
    `appointment_id` INT PRIMARY KEY AUTO_INCREMENT,
    `patient_id` VARCHAR(20) NOT NULL,
    `doctor_id` INT NOT NULL,
    `appointment_date` DATE NOT NULL,
    `start_time` TIME NOT NULL,
    `end_time` TIME NOT NULL,
    `status` VARCHAR(20) DEFAULT 'Booked',
    `notes` TEXT,
    `created_by` INT NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `rescheduled_from_id` INT DEFAULT NULL,
    -- DB-level double-booking backstop: one live (non-cancelled /
    -- non-no-show) booking per (doctor_id, appointment_date, start_time).
    -- NULL for Cancelled/No Show rows so the slot can be re-booked.
    `booking_key` VARCHAR(64) GENERATED ALWAYS AS (
        IF(`status` IN ('Cancelled', 'No Show'), NULL,
           CONCAT_WS('|', `doctor_id`, `appointment_date`, `start_time`))
    ) STORED,
    UNIQUE KEY `uk_appt_booking_key` (`booking_key`),
    FOREIGN KEY (`patient_id`) REFERENCES `patients`(`patient_id`) ON DELETE RESTRICT,
    FOREIGN KEY (`doctor_id`) REFERENCES `doctors`(`doctor_id`) ON DELETE RESTRICT,
    FOREIGN KEY (`created_by`) REFERENCES `users`(`user_id`) ON DELETE RESTRICT,
    FOREIGN KEY (`rescheduled_from_id`) REFERENCES `appointments`(`appointment_id`) ON DELETE SET NULL,
    INDEX `idx_appointment_date_doctor` (`appointment_date`, `doctor_id`),
    INDEX `idx_patient_id` (`patient_id`),
    INDEX `idx_status` (`status`),
    INDEX `idx_doctor_date` (`doctor_id`, `appointment_date`)
) ENGINE=InnoDB;

-- 7. medical_history table
CREATE TABLE IF NOT EXISTS `medical_history` (
    `history_id` INT PRIMARY KEY AUTO_INCREMENT,
    `patient_id` VARCHAR(20) NOT NULL,
    `condition_name` VARCHAR(255) NOT NULL,
    `description` TEXT,
    `diagnosed_date` DATE,
    `status` VARCHAR(20) DEFAULT 'Active',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`patient_id`) REFERENCES `patients`(`patient_id`) ON DELETE CASCADE,
    INDEX `idx_patient_id` (`patient_id`),
    INDEX `idx_status` (`status`)
) ENGINE=InnoDB;

-- 8. visit_records table
CREATE TABLE IF NOT EXISTS `visit_records` (
    `visit_id` INT PRIMARY KEY AUTO_INCREMENT,
    `appointment_id` INT NOT NULL,
    `doctor_id` INT NOT NULL,
    `visit_date` DATE NOT NULL,
    `symptoms` TEXT,
    `diagnosis` TEXT,
    `doctor_notes` TEXT,
    `follow_up_date` DATE,
    `status` VARCHAR(20) DEFAULT 'Completed',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`appointment_id`) REFERENCES `appointments`(`appointment_id`) ON DELETE RESTRICT,
    FOREIGN KEY (`doctor_id`) REFERENCES `doctors`(`doctor_id`) ON DELETE RESTRICT,
    INDEX `idx_appointment_id` (`appointment_id`),
    INDEX `idx_doctor_id` (`doctor_id`),
    INDEX `idx_visit_date` (`visit_date`)
) ENGINE=InnoDB;

-- 9. prescriptions table
CREATE TABLE IF NOT EXISTS `prescriptions` (
    `prescription_id` INT PRIMARY KEY AUTO_INCREMENT,
    `visit_id` INT NOT NULL,
    `medicine_name` VARCHAR(100) NOT NULL,
    `dosage` VARCHAR(50),
    `frequency` VARCHAR(50),
    `duration` VARCHAR(50),
    `instructions` TEXT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`visit_id`) REFERENCES `visit_records`(`visit_id`) ON DELETE CASCADE,
    INDEX `idx_visit_id` (`visit_id`)
) ENGINE=InnoDB;

-- 10. test_reports table
CREATE TABLE IF NOT EXISTS `test_reports` (
    `report_id` INT PRIMARY KEY AUTO_INCREMENT,
    `visit_id` INT NOT NULL,
    `report_name` VARCHAR(100) NOT NULL,
    `file_path` VARCHAR(255) NOT NULL,
    `file_type` VARCHAR(50),
    `file_size` INT,
    `upload_date` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`visit_id`) REFERENCES `visit_records`(`visit_id`) ON DELETE CASCADE,
    INDEX `idx_visit_id` (`visit_id`)
) ENGINE=InnoDB;

-- 11. audit_logs table
CREATE TABLE IF NOT EXISTS `audit_logs` (
    `log_id` INT PRIMARY KEY AUTO_INCREMENT,
    `user_id` INT,
    `action` VARCHAR(100) NOT NULL,
    `target_entity` VARCHAR(50),
    `target_id` VARCHAR(50),
    `old_values` JSON,
    `new_values` JSON,
    `ip_address` VARCHAR(45),
    `user_agent` TEXT,
    `timestamp` TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
    `previous_hash` CHAR(64) DEFAULT NULL,
    `row_hash` CHAR(64) NOT NULL,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`user_id`) ON DELETE SET NULL,
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_timestamp` (`timestamp`),
    INDEX `idx_action` (`action`),
    UNIQUE KEY `uk_audit_row_hash` (`row_hash`)
) ENGINE=InnoDB;

-- Application settings table (key/value preferences, e.g. UI theme)
CREATE TABLE IF NOT EXISTS `app_settings` (
    `setting_key` VARCHAR(100) PRIMARY KEY,
    `setting_value` TEXT,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 12. hospital_holidays table
CREATE TABLE IF NOT EXISTS `hospital_holidays` (
    `holiday_id` INT PRIMARY KEY AUTO_INCREMENT,
    `holiday_date` DATE NOT NULL UNIQUE,
    `holiday_name` VARCHAR(100) NOT NULL,
    `description` TEXT,
    `is_recurring` BOOLEAN DEFAULT FALSE,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_holiday_date` (`holiday_date`)
) ENGINE=InnoDB;

-- 13. doctor_schedules table (for recurring schedules)
CREATE TABLE IF NOT EXISTS `doctor_schedules` (
    `schedule_id` INT PRIMARY KEY AUTO_INCREMENT,
    `doctor_id` INT NOT NULL,
    `day_of_week` TINYINT NOT NULL,
    `start_time` TIME NOT NULL,
    `end_time` TIME NOT NULL,
    `is_available` BOOLEAN DEFAULT TRUE,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`doctor_id`) REFERENCES `doctors`(`doctor_id`) ON DELETE CASCADE,
    UNIQUE KEY `uk_doctor_day` (`doctor_id`, `day_of_week`),
    INDEX `idx_doctor_id` (`doctor_id`)
) ENGINE=InnoDB;

-- 14. doctor_leave table
CREATE TABLE IF NOT EXISTS `doctor_leave` (
    `leave_id` INT PRIMARY KEY AUTO_INCREMENT,
    `doctor_id` INT NOT NULL,
    `leave_start_date` DATE NOT NULL,
    `leave_end_date` DATE NOT NULL,
    `reason` VARCHAR(255),
    `status` VARCHAR(20) DEFAULT 'Approved',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`doctor_id`) REFERENCES `doctors`(`doctor_id`) ON DELETE CASCADE,
    INDEX `idx_doctor_id` (`doctor_id`),
    INDEX `idx_leave_dates` (`leave_start_date`, `leave_end_date`)
) ENGINE=InnoDB;

-- 15. patient_documents table
CREATE TABLE IF NOT EXISTS `patient_documents` (
    `document_id` INT PRIMARY KEY AUTO_INCREMENT,
    `patient_id` VARCHAR(20) NOT NULL,
    `document_name` VARCHAR(100) NOT NULL,
    `file_path` VARCHAR(255) NOT NULL,
    `file_type` VARCHAR(50),
    `file_size` INT,
    `uploaded_by` INT,
    `upload_date` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`patient_id`) REFERENCES `patients`(`patient_id`) ON DELETE CASCADE,
    FOREIGN KEY (`uploaded_by`) REFERENCES `users`(`user_id`) ON DELETE SET NULL,
    INDEX `idx_patient_id` (`patient_id`)
) ENGINE=InnoDB;
"""

SEED_DATA_SQL = """
-- Insert default roles
INSERT IGNORE INTO `roles` (`role_name`, `description`) VALUES 
('Admin', 'System administrator with full access'),
('Doctor', 'Medical doctor with clinical access'),
('Receptionist', 'Front desk staff for patient management');

-- Insert default departments
INSERT IGNORE INTO `departments` (`department_name`, `description`) VALUES 
('General Medicine', 'General medical consultations'),
('Cardiology', 'Heart and cardiovascular diseases'),
('Neurology', 'Nervous system disorders'),
('Orthopedics', 'Bone and joint disorders'),
('Pediatrics', 'Child healthcare'),
('Gynecology', 'Women health'),
('Dermatology', 'Skin diseases'),
('ENT', 'Ear, Nose, and Throat'),
('Ophthalmology', 'Eye care'),
('Psychiatry', 'Mental health');

-- Insert hospital holidays (sample for current year)
INSERT IGNORE INTO `hospital_holidays` (`holiday_date`, `holiday_name`, `description`, `is_recurring`) VALUES
('2026-01-01', 'New Year Day', 'New Year celebration', TRUE),
('2026-01-26', 'Republic Day', 'National holiday', TRUE),
('2026-08-15', 'Independence Day', 'National holiday', TRUE),
('2026-10-02', 'Gandhi Jayanti', 'National holiday', TRUE),
('2026-12-25', 'Christmas Day', 'Christmas celebration', TRUE);
"""


_SCHEMA_TABLE_RE = re.compile(
    r"CREATE TABLE IF NOT EXISTS `([a-z_]+)`", re.IGNORECASE,
)


def _schema_tables() -> List[str]:
    """Return the table names declared by SCHEMA_SQL, in order.

    SCHEMA_SQL is the single source of truth for the application's
    tables; this derives the expected set from it so the schema list
    can never drift from what initialization actually creates.

    Returns:
        Table names as they appear in SCHEMA_SQL.
    """
    return _SCHEMA_TABLE_RE.findall(SCHEMA_SQL)


def initialize_database() -> bool:
    """Initialize database schema and seed data.

    Idempotent by design: every statement uses ``IF NOT EXISTS`` /
    ``INSERT IGNORE``, so re-running on an already-initialized database
    is a no-op.  After the schema executes, every table declared in
    :data:`SCHEMA_SQL` is verified to actually exist — a table added to
    the models/repositories but forgotten in the schema fails startup
    with a clear error instead of a confusing per-query failure later.

    Returns:
        True if the schema is complete, False otherwise.
    """
    try:
        # Create database without specifying it in config.  Uses the
        # elevated admin credentials when configured so the runtime
        # pool can connect as a least-privilege user (no DDL rights).
        config = db_config.get_connection_config(include_db=False, admin=True)
        # DDL is naturally warning-heavy: ``CREATE DATABASE IF NOT
        # EXISTS`` on an existing database emits warning 1007, and
        # ``CREATE TABLE IF NOT EXISTS`` emits 1050 for existing tables.
        # The connection config defaults to ``raise_on_warnings=True``,
        # which would promote the benign 1007 warning into an exception
        # and abort initialization before any schema statement runs.
        # The ``IF NOT EXISTS`` guards already make DDL idempotent, so
        # warnings must never be treated as errors here.
        config["raise_on_warnings"] = False

        import mysql.connector
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()

        # Create database
        database_name = _quoted_identifier(db_config.database)
        create_database_sql = (
            "CREATE DATABASE IF NOT EXISTS " + database_name +
            " CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        use_database_sql = "USE " + database_name
        cursor.execute(create_database_sql)
        cursor.execute(use_database_sql)

        # Execute schema
        statements = [s.strip() for s in SCHEMA_SQL.split(';') if s.strip()]
        for stmt in statements:
            if stmt:
                try:
                    cursor.execute(stmt)
                except mysql.connector.Error as e:
                    if e.errno != 1050:  # Table already exists
                        logger.warning(f"Schema statement warning: {e}")

        # Execute seed data
        seed_statements = [s.strip() for s in SEED_DATA_SQL.split(';') if s.strip()]
        for stmt in seed_statements:
            if stmt:
                try:
                    cursor.execute(stmt)
                except mysql.connector.Error as e:
                    if e.errno != 1062:  # Duplicate entry
                        logger.warning(f"Seed data warning: {e}")

        # Verify every table declared in SCHEMA_SQL now exists.  This is
        # the single reliable completeness check: a table referenced by
        # a model/repository but missing from the schema step is caught
        # at startup with a clear message rather than at first use.
        cursor.execute(
            "SELECT TABLE_NAME FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = %s",
            (db_config.database,),
        )
        existing_tables = {row[0] for row in cursor.fetchall()}
        missing_tables = [t for t in _schema_tables() if t not in existing_tables]
        if missing_tables:
            logger.error(
                "Database initialization incomplete — tables missing: %s",
                ", ".join(missing_tables),
            )
            conn.rollback()
            cursor.close()
            conn.close()
            return False

        conn.commit()
        cursor.close()
        conn.close()

        logger.info("Database initialized successfully")
        return True

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    initialize_database()
