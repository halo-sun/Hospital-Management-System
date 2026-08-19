-- ============================================================================
-- Migration 003 — app_settings table
-- ============================================================================
-- Adds the key/value preference table used to persist application-level
-- settings (currently the UI theme choice: 'flatly' / 'darkly').  Fresh
-- databases get this table automatically from src/database/init_db.py;
-- this migration is for existing databases only.
--
-- Usage (run once as a MySQL admin against the existing database):
--     mysql -u <admin> -p hospital_db < database/migrations/003_app_settings.sql
-- ============================================================================

USE `hospital_db`;

CREATE TABLE IF NOT EXISTS `app_settings` (
    `setting_key`   VARCHAR(100)  NOT NULL,
    `setting_value` TEXT,
    `updated_at`    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (`setting_key`)
) ENGINE=InnoDB;
