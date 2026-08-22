-- ============================================================================
-- Migration 005 — Add working_hours columns to doctors table
-- ============================================================================
-- These columns were added to the CREATE TABLE schema after the initial
-- database was created.  Installs that ran init_db before these columns
-- existed silently lack them, causing doctor creation to fail.
--
-- MySQL does NOT support "ADD COLUMN IF NOT EXISTS" (that's MariaDB syntax).
-- This migration uses a stored procedure to check information_schema first
-- and only runs ALTER TABLE when the columns are actually missing.
--
-- Safe to re-run: will skip columns that already exist.
--
-- Usage:
--     mysql -u <admin> -p hospital_db < database/migrations/005_doctor_working_hours.sql
-- ============================================================================

USE `hospital_db`;

-- Drop the procedure if it already exists from a previous run
DROP PROCEDURE IF EXISTS `_add_working_hours_columns`;

DELIMITER $$

CREATE PROCEDURE `_add_working_hours_columns`()
BEGIN
    -- Check for working_hours_start
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'doctors'
          AND COLUMN_NAME = 'working_hours_start'
    ) THEN
        ALTER TABLE `doctors`
            ADD COLUMN `working_hours_start` TIME DEFAULT NULL;
    END IF;

    -- Check for working_hours_end
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'doctors'
          AND COLUMN_NAME = 'working_hours_end'
    ) THEN
        ALTER TABLE `doctors`
            ADD COLUMN `working_hours_end` TIME DEFAULT NULL;
    END IF;
END$$

DELIMITER ;

-- Execute the migration
CALL `_add_working_hours_columns`();

-- Clean up the temporary procedure
DROP PROCEDURE IF EXISTS `_add_working_hours_columns`;

-- Verify the columns exist
SELECT
    COLUMN_NAME,
    COLUMN_TYPE,
    IS_NULLABLE
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'doctors'
  AND COLUMN_NAME IN ('working_hours_start', 'working_hours_end')
ORDER BY ORDINAL_POSITION;
