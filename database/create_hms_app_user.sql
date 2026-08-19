-- ============================================================================
-- Least-privilege MySQL user for the application runtime
-- ============================================================================
-- Creates the `hms_app` account used by the app's connection pool.
-- The account is granted DML only (SELECT / INSERT / UPDATE / DELETE) on
-- `hospital_db` — no DDL (CREATE / ALTER / DROP), no GRANT, no other
-- databases.  Schema creation is a one-time, elevated operation that runs
-- with the DB_ADMIN_USER credentials (or the app user if it still has DDL
-- rights).
--
-- Usage (run once as a MySQL admin):
--     sudo mysql < database/create_hms_app_user.sql
--
-- Then point the app at it via `.env`:
--     DB_USER=hms_app
--     DB_PASSWORD=<the password set below>
--
-- NOTE: the database and tables must already exist (or be created once with
-- elevated credentials) before this user can do anything.
-- ============================================================================

-- MySQL prints the generated credential once. Store it in the deployment
-- secret manager, then configure it as DB_PASSWORD; never commit it.
CREATE USER IF NOT EXISTS 'hms_app'@'localhost' IDENTIFIED BY RANDOM PASSWORD;

GRANT SELECT, INSERT, UPDATE, DELETE ON `hospital_db`.* TO 'hms_app'@'localhost';

FLUSH PRIVILEGES;
