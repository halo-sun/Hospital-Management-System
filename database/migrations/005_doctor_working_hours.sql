-- 005: Add missing working_hours columns to doctors table
-- These columns were added to the CREATE TABLE schema after the initial
-- database was created.  IF NOT EXISTS does NOT add new columns to an
-- existing table, so installs that ran init_db before these columns
-- existed silently lack them, causing doctor creation to fail with a
-- cryptic MySQL column error.

ALTER TABLE `doctors`
    ADD COLUMN IF NOT EXISTS `working_hours_start` TIME DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS `working_hours_end` TIME DEFAULT NULL;

-- Verify the columns were added (will fail loudly if ALTER didn't work)
SELECT
    COLUMN_NAME,
    COLUMN_TYPE,
    IS_NULLABLE
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'doctors'
  AND COLUMN_NAME IN ('working_hours_start', 'working_hours_end')
ORDER BY ORDINAL_POSITION;
