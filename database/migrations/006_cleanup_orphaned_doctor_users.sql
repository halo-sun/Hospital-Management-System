-- 006: Clean up orphaned doctor user accounts
-- These were created when doctor creation failed mid-way (user row
-- committed, doctor row failed due to missing columns or other errors).
-- The atomic transaction fix in doctor_service prevents future orphans;
-- this migration removes existing ones.

-- STEP 1: Preview what will be deleted (run this first and confirm)
SELECT
    u.user_id,
    u.username,
    u.full_name,
    u.role_id,
    u.created_at
FROM users u
JOIN roles r ON u.role_id = r.role_id
WHERE r.role_name = 'Doctor'
  AND NOT EXISTS (
      SELECT 1 FROM doctors d WHERE d.user_id = u.user_id
  );

-- STEP 2: After confirming the rows above are the orphaned accounts,
-- uncomment and run the DELETE below.
-- DELETE u FROM users u
-- JOIN roles r ON u.role_id = r.role_id
-- WHERE r.role_name = 'Doctor'
--   AND NOT EXISTS (
--       SELECT 1 FROM doctors d WHERE d.user_id = u.user_id
--   );
