-- Adds a tamper-evident SHA-256 hash chain to existing audit logs.
-- Run the companion Python backfill once after this DDL so historical rows
-- receive deterministic hashes before the application writes new entries.
ALTER TABLE `audit_logs`
    MODIFY COLUMN `timestamp` TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    ADD COLUMN `previous_hash` CHAR(64) NULL AFTER `timestamp`,
    ADD COLUMN `row_hash` CHAR(64) NULL AFTER `previous_hash`,
    ADD UNIQUE KEY `uk_audit_row_hash` (`row_hash`);
