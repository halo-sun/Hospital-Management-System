-- ============================================================================
-- Hospital Scheduling System – Seed / Reference Data
-- ============================================================================
-- Usage:  mysql -u root -p hospital_db < seed.sql

USE `hospital_db`;

-- ── 1. ROLES ───────────────────────────────────────────────────────────────
INSERT INTO `roles` (`role_name`, `description`) VALUES
    ('Admin',        'System administrator with full access'),
    ('Doctor',       'Medical doctor with clinical access'),
    ('Receptionist', 'Front-desk staff for patient management')
ON DUPLICATE KEY UPDATE `role_id` = `role_id`;

-- ── 2. DEPARTMENTS ─────────────────────────────────────────────────────────
INSERT INTO `departments` (`department_name`, `description`) VALUES
    ('General Medicine', 'General medical consultations and primary care'),
    ('Cardiology',       'Heart and cardiovascular system diseases'),
    ('Neurology',        'Nervous system disorders and brain health'),
    ('Orthopedics',      'Bone, joint, and musculoskeletal disorders'),
    ('Pediatrics',       'Child healthcare from infancy to adolescence'),
    ('Gynecology',       'Women reproductive health and pregnancy care'),
    ('Dermatology',      'Skin, hair, and nail diseases'),
    ('ENT',              'Ear, Nose, and Throat disorders'),
    ('Ophthalmology',    'Eye care and vision disorders'),
    ('Psychiatry',       'Mental health and behavioral disorders')
ON DUPLICATE KEY UPDATE `department_id` = `department_id`;

-- ── 3. SAMPLE DOCTOR USERS ────────────────────────────────────────────────
-- Demo users with a non-functional placeholder hash (cannot log in);
-- real accounts are created through the application.
INSERT INTO `users` (`username`, `password_hash`, `role_id`, `status`, `email`, `full_name`) VALUES
    ('dr.sharma',  '$2b$12$LJ3m4ys3Lk0TSwHnbfOMiOXPm1Qlq5Gz0Y0d5q5Gz0Y0d5q5Gz0O', (SELECT `role_id` FROM `roles` WHERE `role_name` = 'Doctor'), 'Active', 'sharma@hospital.com',  'Dr. Amit Sharma'),
    ('dr.patel',   '$2b$12$LJ3m4ys3Lk0TSwHnbfOMiOXPm1Qlq5Gz0Y0d5q5Gz0Y0d5q5Gz0O', (SELECT `role_id` FROM `roles` WHERE `role_name` = 'Doctor'), 'Active', 'patel@hospital.com',   'Dr. Priya Patel'),
    ('dr.verma',   '$2b$12$LJ3m4ys3Lk0TSwHnbfOMiOXPm1Qlq5Gz0Y0d5q5Gz0Y0d5q5Gz0O', (SELECT `role_id` FROM `roles` WHERE `role_name` = 'Doctor'), 'Active', 'verma@hospital.com',   'Dr. Rajesh Verma'),
    ('dr.singh',   '$2b$12$LJ3m4ys3Lk0TSwHnbfOMiOXPm1Qlq5Gz0Y0d5q5Gz0Y0d5q5Gz0O', (SELECT `role_id` FROM `roles` WHERE `role_name` = 'Doctor'), 'Active', 'singh@hospital.com',   'Dr. Neha Singh')
ON DUPLICATE KEY UPDATE `user_id` = `user_id`;

-- ── 4. SAMPLE RECEPTIONIST USER ────────────────────────────────────────────
-- Demo user with a non-functional placeholder hash (cannot log in).
INSERT INTO `users` (`username`, `password_hash`, `role_id`, `status`, `email`, `full_name`) VALUES
    ('reception', '$2b$12$LJ3m4ys3Lk0TSwHnbfOMiOXPm1Qlq5Gz0Y0d5q5Gz0Y0d5q5Gz0O', (SELECT `role_id` FROM `roles` WHERE `role_name` = 'Receptionist'), 'Active', 'frontdesk@hospital.com', 'Sunita Gupta')
ON DUPLICATE KEY UPDATE `user_id` = `user_id`;

-- ── 5. DOCTOR PROFILES ────────────────────────────────────────────────────
INSERT INTO `doctors` (`user_id`, `department_id`, `full_name`, `specialization`, `contact_number`, `email`, `qualification`, `license_number`, `experience_years`, `consultation_fee`, `max_appointments_per_day`, `status`)
SELECT
    u.`user_id`,
    d.`department_id`,
    u.`full_name`,
    CASE u.`username`
        WHEN 'dr.sharma' THEN 'Cardiology'
        WHEN 'dr.patel'  THEN 'Neurology'
        WHEN 'dr.verma'  THEN 'Orthopedics'
        WHEN 'dr.singh'  THEN 'Pediatrics'
    END,
    CASE u.`username`
        WHEN 'dr.sharma' THEN '+91-9876543210'
        WHEN 'dr.patel'  THEN '+91-9876543211'
        WHEN 'dr.verma'  THEN '+91-9876543212'
        WHEN 'dr.singh'  THEN '+91-9876543213'
    END,
    u.`email`,
    CASE u.`username`
        WHEN 'dr.sharma' THEN 'MD, DM (Cardiology)'
        WHEN 'dr.patel'  THEN 'MD, DM (Neurology)'
        WHEN 'dr.verma'  THEN 'MS (Orthopedics)'
        WHEN 'dr.singh'  THEN 'MD (Pediatrics)'
    END,
    CASE u.`username`
        WHEN 'dr.sharma' THEN 'MCI-2020-001'
        WHEN 'dr.patel'  THEN 'MCI-2020-002'
        WHEN 'dr.verma'  THEN 'MCI-2020-003'
        WHEN 'dr.singh'  THEN 'MCI-2020-004'
    END,
    CASE u.`username`
        WHEN 'dr.sharma' THEN 12
        WHEN 'dr.patel'  THEN 8
        WHEN 'dr.verma'  THEN 15
        WHEN 'dr.singh'  THEN 5
    END,
    CASE u.`username`
        WHEN 'dr.sharma' THEN 800.00
        WHEN 'dr.patel'  THEN 1000.00
        WHEN 'dr.verma'  THEN 600.00
        WHEN 'dr.singh'  THEN 500.00
    END,
    20,
    'Active'
FROM `users` u
JOIN `departments` d ON d.`department_name` = CASE u.`username`
    WHEN 'dr.sharma' THEN 'Cardiology'
    WHEN 'dr.patel'  THEN 'Neurology'
    WHEN 'dr.verma'  THEN 'Orthopedics'
    WHEN 'dr.singh'  THEN 'Pediatrics'
END
WHERE u.`role_id` = (SELECT `role_id` FROM `roles` WHERE `role_name` = 'Doctor');

-- ── 6. DOCTOR SCHEDULES (Mon–Fri, 9 AM – 5 PM) ────────────────────────────
INSERT INTO `doctor_schedules` (`doctor_id`, `day_of_week`, `start_time`, `end_time`, `lunch_break_start`, `lunch_break_end`, `is_available`, `slot_duration`)
SELECT
    doc.`doctor_id`,
    days.`dow`,
    '09:00:00',
    '17:00:00',
    '13:00:00',
    '14:00:00',
    TRUE,
    15
FROM `doctors` doc
CROSS JOIN (
    SELECT 1 AS `dow` UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
) days
WHERE doc.`status` = 'Active';

-- ── 7. SAMPLE PATIENTS ────────────────────────────────────────────────────
INSERT INTO `patients` (`patient_id`, `full_name`, `date_of_birth`, `gender`, `contact_number`, `email`, `address`, `emergency_contact_name`, `emergency_contact_number`, `blood_group`, `allergies`) VALUES
    ('PAT-00001', 'Ravi Kumar',      '1985-03-15', 'Male',   '+91-9988776651', 'ravi@email.com',    '12, MG Road, Mumbai',       'Sita Devi',     '+91-9988776601', 'O+',  'Pollen'),
    ('PAT-00002', 'Ananya Reddy',    '1992-07-22', 'Female', '+91-9988776652', 'ananya@email.com',  '45, Brigade Road, Bangalore','Rajesh Reddy',  '+91-9988776602', 'B+',  'None'),
    ('PAT-00003', 'Vikram Singh',    '1978-11-08', 'Male',   '+91-9988776653', 'vikram@email.com',  '78, Park Street, Kolkata',  'Meera Singh',   '+91-9988776603', 'A+',  'Penicillin'),
    ('PAT-00004', 'Lakshmi Nair',    '1995-05-30', 'Female', '+91-9988776654', 'lakshmi@email.com', '23, Jubilee Hills, Hyderabad','Arun Nair',    '+91-9988776604', 'AB+', 'Sulfa drugs'),
    ('PAT-00005', 'Arjun Mehta',     '2000-01-12', 'Male',   '+91-9988776655', 'arjun@email.com',   '56, CP, New Delhi',         'Kavita Mehta',  '+91-9988776605', 'O-',  'Dust'),
    ('PAT-00006', 'Sunita Deshmukh', '1989-09-17', 'Female', '+91-9988776656', 'sunita@email.com',  '90, FC Road, Pune',         'Amit Deshmukh', '+91-9988776606', 'B-',  'None'),
    ('PAT-00007', 'Rohit Joshi',     '1975-12-03', 'Male',   '+91-9988776657', 'rohit@email.com',   '34, Civil Lines, Delhi',    'Pooja Joshi',   '+91-9988776607', 'A-',  'Aspirin'),
    ('PAT-00008', 'Priya Sharma',    '2002-04-25', 'Female', '+91-9988776658', 'priya@email.com',   '67, Link Road, Jaipur',     'Mohan Sharma',  '+91-9988776608', 'AB-', 'Peanuts')
ON DUPLICATE KEY UPDATE `patient_id` = `patient_id`;

-- ── 8. SAMPLE APPOINTMENTS (today) ─────────────────────────────────────────
INSERT INTO `appointments` (`patient_id`, `doctor_id`, `appointment_date`, `start_time`, `end_time`, `status`, `notes`, `created_by`)
SELECT
    'PAT-00001',
    d.`doctor_id`,
    CURDATE(),
    '09:00:00',
    '09:30:00',
    'Booked',
    'Routine check-up',
    (SELECT `user_id` FROM `users` WHERE `username` = 'reception')
FROM `doctors` d WHERE d.`full_name` = 'Dr. Amit Sharma'
UNION ALL
SELECT 'PAT-00002', d.`doctor_id`, CURDATE(), '09:30:00', '10:00:00', 'Booked', 'Headache consultation', (SELECT `user_id` FROM `users` WHERE `username` = 'reception')
FROM `doctors` d WHERE d.`full_name` = 'Dr. Amit Sharma'
UNION ALL
SELECT 'PAT-00003', d.`doctor_id`, CURDATE(), '10:00:00', '10:30:00', 'Booked', 'ECG follow-up', (SELECT `user_id` FROM `users` WHERE `username` = 'reception')
FROM `doctors` d WHERE d.`full_name` = 'Dr. Amit Sharma'
UNION ALL
SELECT 'PAT-00004', d.`doctor_id`, CURDATE(), '09:00:00', '09:45:00', 'Booked', 'Migraine consultation', (SELECT `user_id` FROM `users` WHERE `username` = 'reception')
FROM `doctors` d WHERE d.`full_name` = 'Dr. Priya Patel'
UNION ALL
SELECT 'PAT-00005', d.`doctor_id`, CURDATE(), '11:00:00', '11:30:00', 'Booked', 'Knee pain', (SELECT `user_id` FROM `users` WHERE `username` = 'reception')
FROM `doctors` d WHERE d.`full_name` = 'Dr. Rajesh Verma'
UNION ALL
SELECT 'PAT-00006', d.`doctor_id`, CURDATE(), '14:00:00', '14:30:00', 'Booked', 'Child fever', (SELECT `user_id` FROM `users` WHERE `username` = 'reception')
FROM `doctors` d WHERE d.`full_name` = 'Dr. Neha Singh';

-- ── 9. HOSPITAL HOLIDAYS ─────────────────────────────────────────────────
INSERT INTO `hospital_holidays` (`holiday_date`, `holiday_name`, `description`, `is_recurring`) VALUES
    ('2026-01-01', 'New Year Day',        'New Year celebration',           TRUE),
    ('2026-01-26', 'Republic Day',        'National holiday',               TRUE),
    ('2026-08-15', 'Independence Day',    'National holiday',               TRUE),
    ('2026-10-02', 'Gandhi Jayanti',      'National holiday',               TRUE),
    ('2026-12-25', 'Christmas Day',       'Christmas celebration',          TRUE)
ON DUPLICATE KEY UPDATE `holiday_id` = `holiday_id`;
