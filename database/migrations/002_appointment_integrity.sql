-- ============================================================================
-- Migration 002 — Appointment integrity backstops
-- ============================================================================
-- Adds to `appointments`:
--   1. `rescheduled_from_id` — links a reschedule to the original row
--      (rescheduling inserts a NEW row instead of mutating in place).
--   2. `booking_key` — a STORED generated column that is NULL for
--      Cancelled / No Show rows and the composite
--      (doctor_id | appointment_date | start_time) otherwise, with a
--      UNIQUE index on it.  This is the DB-level double-booking backstop:
--      MySQL cannot have two live bookings for the same doctor/date/slot,
--      while cancelled rows (NULL) leave the slot re-bookable.
--
-- Prerequisite: the table must not already contain duplicate live
-- bookings for the same (doctor_id, appointment_date, start_time).
-- Deduplicate first, otherwise the ALTER will fail with a duplicate-key
-- error on the new unique index.
--
-- Usage (run once as a MySQL admin against the existing database):
--     mysql -u <admin> -p hospital_db < database/migrations/002_appointment_integrity.sql
-- ============================================================================

USE `hospital_db`;

ALTER TABLE `appointments`
    ADD COLUMN `rescheduled_from_id` INT DEFAULT NULL AFTER `updated_at`,
    ADD COLUMN `booking_key` VARCHAR(64) GENERATED ALWAYS AS (
        IF(`status` IN ('Cancelled', 'No Show'), NULL,
           CONCAT_WS('|', `doctor_id`, `appointment_date`, `start_time`))
    ) STORED AFTER `rescheduled_from_id`,
    ADD UNIQUE KEY `uk_appt_booking_key` (`booking_key`),
    ADD KEY `idx_appt_rescheduled_from` (`rescheduled_from_id`),
    ADD CONSTRAINT `fk_appt_rescheduled_from` FOREIGN KEY (`rescheduled_from_id`)
        REFERENCES `appointments` (`appointment_id`) ON DELETE SET NULL ON UPDATE CASCADE;
