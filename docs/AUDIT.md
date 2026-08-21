# 🔍 Comprehensive Codebase Audit Report

> **Date:** August 21, 2026
> **Scope:** Full codebase — security, logical correctness, consistency, code quality
> **Mode:** Read-only diagnostic pass (no files modified)
> **Test Suite:** 525 passed, 0 failed, 0 skipped

---

## PART 1 — SECURITY RE-AUDIT

### 1.1 SQL Injection

| Severity | Location | Issue | Suggested Fix |
|---|---|---|---|
| 🟡 MINOR | `src/gui/setup/setup_wizard_view.py:564-566` | `f"GRANT ... ON \`{db_name}\`.* TO ..."` — `db_name` comes from `os.getenv("DB_NAME", "hospital_db")`. This is an env var, not user input, so exploitation requires a compromised env file. However, the value is interpolated into a SQL GRANT statement via f-string. | Use a whitelist check or escape `db_name` before interpolation. Alternatively, restructure to use a parameterized DCL statement (MySQL Connector supports parameterized GRANT). |
| ✅ PASS | `src/repositories/base_repository.py` | All repository queries use `%s` parameterized placeholders for **values**. Column/table names are from `self.table_name` (set at class init, not from user input). | No fix needed. |
| ✅ PASS | `src/repositories/base_repository.py:15-21` | `_ORDER_BY_RE` regex allow-list prevents SQL injection in ORDER BY clauses. Anything not matching `^[A-Za-z0-9_]+(\s+(ASC|DESC))?...` is rejected. | No fix needed. |
| ✅ PASS | `src/services/document_service.py` | File upload paths use UUID4 random names, never user-supplied path text. `resolve_upload_path` confirms containment via `os.path.realpath`. | No fix needed. |

### 1.2 RBAC Coverage (file-by-file)

| Controller | Methods | All RBAC-gated? | Notes |
|---|---|---|---|
| `auth_controller.py` | `login`, `logout`, `change_password`, `reset_password`, `get_all_users`, `get_user`, etc. | ✅ | `login`/`logout`/`restore_session` correctly un-gated (pre-auth). Admin-only methods have `@require_role(Role.ADMIN)`. |
| `patient_controller.py` | 10 methods | ✅ | All gated: RECEPTIONIST+ADMIN for most, ADMIN-only for delete/bulk. |
| `doctor_controller.py` | 18 methods | ✅ | All gated. `get_all_doctors` allows ADMIN+RECEPTIONIST (correct for booking flow). |
| `appointment_controller.py` | 15 methods | ✅ | All gated. |
| `clinical_controller.py` | 14 methods | ✅ | All gated to `Role.DOCTOR`. |
| `document_controller.py` | 4 methods | ✅ | All gated to `Role.DOCTOR`. |
| `staff_controller.py` | 9 methods | ✅ | All gated to `Role.ADMIN`. |
| `department_controller.py` | 5 methods | ✅ | All gated to `Role.ADMIN`. |
| `audit_controller.py` | 1 method | ✅ | Gated to `Role.ADMIN`. |
| `settings_controller.py` | 6 methods | ✅ | All gated to `Role.ADMIN`. |
| `report_controller.py` | 16 methods | ✅ | All gated (ADMIN for admin reports, DOCTOR for doctor dashboard). |
| `setup_controller.py` | 4 methods | ✅ N/A | Correctly un-gated — runs before any user is logged in (first-run wizard). |

### 1.3 Auth & Session Security

| Severity | Location | Issue | Suggested Fix |
|---|---|---|---|
| ✅ PASS | `src/services/auth_service.py:392-394` | bcrypt cost factor uses `app_config.bcrypt_rounds` (= 12). Not hardcoded. | No fix needed. |
| ✅ PASS | `src/services/auth_service.py:159-162` | Account lockout: after `MAX_LOGIN_ATTEMPTS` (5) failures, account is locked for `LOCKOUT_DURATION_MINUTES` (15). Uses DB-level timestamp. | No fix needed. |
| ✅ PASS | `src/services/auth_service.py:219-231` | Session timeout: `is_session_expired()` checks `_session_start` against `session_timeout_minutes` (30). | No fix needed. |
| ✅ PASS | `src/auth/remember_token.py:31-32` | Token generation uses `secrets.token_hex(32)` — 64-char hex string from `os.urandom`. | No fix needed. |
| ✅ PASS | `src/services/auth_service.py:219-231` | Session timeout check happens on the main window's 30-second clock ticker (`_update_clock`), not mid-action. | Acceptable for desktop app. |

### 1.4 Scheduling Engine Transaction Discipline

| Severity | Location | Issue | Suggested Fix |
|---|---|---|---|
| ✅ PASS | `src/services/appointment_service.py:64-65,106` | `SELECT ... FOR UPDATE` used in `book_appointment` and `reschedule_appointment`. Both wrap the check-then-write in `DatabaseConnection.transaction()`. | No fix needed. |
| ✅ PASS | `src/services/appointment_service.py:132-137` | Deadlock detection: `except mysql.connector.IntegrityError` catches deadlock victims and returns slot-conflict message. | No fix needed. |
| ✅ PASS | `src/repositories/audit_repository.py:33` | Audit log insert also uses `SELECT ... FOR UPDATE` on the last hash before computing the new one. | No fix needed. |

### 1.5 File Upload Validation

| Severity | Location | Issue | Suggested Fix |
|---|---|---|---|
| ✅ PASS | `src/services/document_service.py:56-90` | Extension allow-list (`.pdf`, `.jpg`, `.jpeg`, `.png`, `.dcm`), magic-byte verification, 10MB size cap checked before read, UUID4 storage names. | No fix needed. |
| ✅ PASS | `src/services/document_service.py:138-155` | Path traversal protection: `resolve_upload_path` uses `os.path.realpath` + `startswith` check to confirm containment. | No fix needed. |

### 1.6 Audit Log Hash Chain

| Severity | Location | Issue | Suggested Fix |
|---|---|---|---|
| ✅ PASS | `src/repositories/audit_repository.py:33-38` | Every insert: fetches last `row_hash` with `FOR UPDATE`, computes SHA-256 of canonical data + previous hash. | No fix needed. |
| ✅ PASS | `src/repositories/audit_repository.py:177-183` | `verify_hash_chain()` validates both chain linkage (`previous_hash` matches) and content integrity (`row_hash` matches recomputation). | No fix needed. |

### 1.7 Hardcoded Credentials

| Severity | Location | Issue | Suggested Fix |
|---|---|---|---|
| ✅ PASS | `src/controllers/setup_controller.py:30-33` | Strings like "admin123", "password123" appear only in a **password blocklist** (weak passwords rejected during setup), not as actual credentials. | No fix needed. |
| ✅ PASS | `src/database/seed_demo_data.py:114-116` | Demo passwords sourced from `os.getenv("HMS_SEED_ADMIN_PASSWORD")` etc. — never hardcoded. | No fix needed. |
| ✅ PASS | `.env.example` | Contains only placeholder/empty values. No real credentials. | No fix needed. |
| ✅ PASS | `.gitignore` | `.env` and `.env.*` (except `.env.example`) are gitignored. | No fix needed. |

---

## PART 2 — LOGICAL CORRECTNESS AUDIT

### 2.1 Scheduling Engine Validation Pipeline

| Severity | Location | Issue | Suggested Fix |
|---|---|---|---|
| 🟡 MINOR | `src/services/scheduling_engine.py:88-163` | **Docstring/implementation mismatch.** The docstring at line 88-97 lists 9 steps (1. Doctor, 2. Holiday, 3. Leave, 4. Day-of-week, 5. Working hours, 6. Lunch, 7. Overlap, 8. Daily limit, 9. Past date), but the implementation has 7 numbered comments (1-7) because steps 4-6 are collapsed into `_check_day_schedule`. This is a documentation inaccuracy, not a logic bug. | Update the docstring to match the actual 7-step pipeline, or expand the comments to list all 9 sub-checks. |
| ✅ PASS | Lines 122-163 | The actual validation order is correct: Doctor→Active, Holiday, Leave, Day-schedule (which internally checks day-of-week, working hours, lunch), Overlap, Daily limit, Past date. Past-date is correctly last. | No fix needed. |
| ✅ PASS | Lines 113-115 | `existing_appointments` parameter correctly passes locked rows from the transaction snapshot into overlap and daily-limit checks. | No fix needed. |

### 2.2 Reschedule / Cancel Logic

| Severity | Location | Issue | Suggested Fix |
|---|---|---|---|
| ✅ PASS | `src/services/appointment_service.py:260-305` | Reschedule correctly creates a new row with `rescheduled_from_id`, then cancels the original — never mutates the original. Both happen inside a `transaction()` with `FOR UPDATE` locking. | No fix needed. |
| ✅ PASS | `src/services/appointment_service.py:246-256` | Cancel only changes status to 'Cancelled' (status update, never a delete). Only 'Booked' appointments can be cancelled. | No fix needed. |

### 2.3 Filter / Sort / Search Correctness

| Severity | Location | Issue | Suggested Fix |
|---|---|---|---|
| 🟡 MINOR | `src/controllers/doctor_controller.py:273-291` | `filter_doctors()` method is **dead code** — the doctor management view now does client-side filtering and never calls this method. It still exists in both `doctor_controller.py` and `doctor_service.py`. | Remove `filter_doctors()` from `doctor_controller.py` and `doctor_service.py` to reduce confusion. |
| 🟡 MINOR | `src/repositories/appointment_repository.py:63-68` | `find_by_doctor_and_date` filters for `status IN ('Booked', 'Completed')`. This means cancelled/rescheduled appointments are excluded from the locked snapshot used for overlap checks. This is correct (cancelled rows can't overlap) but means a **concurrent reschedule** that cancels a booking doesn't get visible to the other transaction's overlap check via this query — it's handled instead by the `FOR UPDATE` lock blocking the concurrent transaction. | No fix needed — the lock-based approach is sound. Document this intentional design choice in the query's docstring. |
| ✅ PASS | `src/gui/admin/doctor_management_view.py:255-315` | Client-side AND-filtering across department, specialization, status, and text search. All four compose correctly. Clear button resets all. | No fix needed. |
| ✅ PASS | `src/gui/common/base_view.py:225-240` | Sort parser tries DD-MM-YYYY first, then YYYY-MM-DD, then HH:MM — correctly handles the new date format. | No fix needed. |
| ✅ PASS | `src/repositories/base_repository.py:15-21` | `_ORDER_BY_RE` regex rejectlist ensures sort columns can't contain injection payloads. | No fix needed. |

### 2.4 Date Format Migration (DD-MM-YYYY)

| Severity | Location | Issue | Suggested Fix |
|---|---|---|---|
| 🟡 MINOR | `src/utils/formatters.py:83-93` | `_parse_date_string` tries DD-MM-YYYY first, then YYYY-MM-DD. This means **ambiguous dates** like "01-02-2026" are always interpreted as 1-Feb (DD-MM), never 2-Jan. This is the intended behavior per the DD-MM-YYYY convention, but there's no logging when the fallback format is used, which could make debugging tricky if a user types in an unexpected format. | Consider adding a debug log when the non-canonical format is matched, for diagnostic purposes. |
| ✅ PASS | All 11 date locations from the last audit (doctor_schedule_dialog, settings_view, reports_view, analytics_dashboard_view, audit_log_view, clinical_views×3, user_management_view, staff_management_view, main_window) | All now use `format_date()` / `format_datetime()` / `parse_date_for_input()` from the shared `formatters.py`. No ad-hoc `strftime` calls remain (verified via grep). | No fix needed. |
| ✅ PASS | `src/services/scheduling_engine.py:163` | Past-date check uses `date.today()` comparison — a `date` object, unaffected by display format. | No fix needed. |
| ✅ PASS | `src/utils/validators.py:93-120` | `validate_date_of_birth` tries all 4 formats (DD-MM-YYYY, YYYY-MM-DD, YYYY/MM/DD, DD/MM/YYYY) — correctly backwards-compatible. Age calculation uses `date` objects, unaffected by display format. | No fix needed. |

### 2.5 RBAC Edge Cases

| Severity | Location | Issue | Suggested Fix |
|---|---|---|---|
| 🟠 MAJOR | `src/controllers/clinical_controller.py:178-195` | **No doctor-to-doctor access isolation.** `get_doctor_visits(doctor_id)` accepts any `doctor_id` — Doctor A could theoretically call this method with Doctor B's ID and see all of Doctor B's visit records. The `@require_role(Role.DOCTOR)` only verifies the caller is *a* doctor, not *the specific* doctor. In practice, the GUI never exposes other doctors' IDs (the sidebar only shows "My Schedule" and the doctor's own data), but the **controller API** doesn't enforce this. | Add a check: `if doctor_id != self._auth_ctrl.current_user.get("doctor_id")` → reject. This matters if the API is ever called programmatically or if a future feature exposes another doctor's data. |
| 🟠 MAJOR | `src/controllers/document_controller.py:51-80` | Same pattern: `upload_document(patient_id, ...)` and `list_documents(patient_id)` accept any `patient_id`. A doctor could upload/view/delete documents for any patient, not just patients they've seen. The RBAC decorator only checks "is a doctor." | Add a check against the doctor's own patient list (via `clinical_service.get_doctor_visits`) or maintain a doctor-patient association table for access control. |
| 🟡 MINOR | `src/app.py:476-485` | Session expiry: If a session expires mid-operation (e.g. during a multi-step booking wizard), the clock ticker shows a warning and calls `_handle_logout()`. The wizard state is lost. This is acceptable for a desktop app but could leave partial DB state if the user had clicked "Book" just as the session expired (the DB-level `FOR UPDATE` transaction would roll back, so data integrity is safe, but UX is confusing). | Consider adding a session-refresh on any user action (reset `_session_start` on every click), which is standard for timeout-based sessions. |

### 2.6 Race Conditions

| Severity | Location | Issue | Suggested Fix |
|---|---|---|---|
| 🔵 IMPROVEMENT | `src/controllers/doctor_controller.py` (edit/delete), `staff_controller.py` (edit/delete), `patient_controller.py` (edit/delete) | Two admins editing the same record simultaneously could cause a lost update (last write wins). No optimistic locking (e.g. version column or `WHERE updated_at = <old_value>`). | Acceptable for a single-instance desktop app. If multi-instance support is ever needed, add an `updated_at` version check. |
| ✅ PASS | `src/services/appointment_service.py` | Booking/reschedule uses `FOR UPDATE` + transaction. Deadlock-safe with `except IntegrityError` fallback. | No fix needed. |

### 2.7 Reports Module Correctness

| Severity | Location | Issue | Suggested Fix |
|---|---|---|---|
| 🟡 MINOR | `src/services/report_service.py:189-202` | `get_cancellation_rate`: The `count_total_by_date_range` counts **non-cancelled** appointments. Then `total_count = t + c` adds the cancelled count back. This is mathematically correct (cancelled + non-cancelled = total), but the variable name `total` in the repository query is misleading — it actually counts non-cancelled. | Rename the repository method to `count_non_cancelled_by_date_range` or add a clarifying comment. The math is correct; just the naming is confusing. |
| ✅ PASS | `src/services/report_service.py:41-55` | `get_daily_appointments` uses `find_by_date_range` which returns all statuses (not filtered). Correct for a raw data report. | No fix needed. |
| ✅ PASS | `src/services/report_service.py:54-80` | `get_monthly_appointments` correctly computes month boundaries (handles December→January rollover). | No fix needed. |

### 2.8 Form Validation Consistency

| Severity | Location | Issue | Suggested Fix |
|---|---|---|---|
| 🔵 IMPROVEMENT | `src/utils/validators.py` vs GUI forms | The validator has thorough rules (name regex, phone regex, email regex, DOB format, age range, etc.), but not all GUI forms call every relevant validator. For example, the patient registration form validates DOB and required fields, but the doctor form's email validation may use a simpler check. | Centralize all validation through the shared `validators.py` functions and ensure every form calls them. This is a consistency improvement, not a bug. |

---

## PART 3 — CONSISTENCY & REGRESSION RISK AUDIT

### 3.1 Dead / Duplicate Code

| Severity | Location | Issue | Suggested Fix |
|---|---|---|---|
| 🟡 MINOR | `src/controllers/doctor_controller.py:273-291` + `src/services/doctor_service.py:245+` | `filter_doctors()` is dead code — the view does client-side filtering and never calls this. The old `on_filter` callback used to trigger this, but Phase 2 (client-side filtering) made it unnecessary. | Remove the method from both controller and service. |
| 🟡 MINOR | `src/factories/admin_factory.py` | `_handle_doctor_search` and `_handle_doctor_filter` were removed in Phase 2, but the `_apply_view_filters` lambda now only calls `view._apply_filters()` — the `on_search` and `on_filter` callback signatures in `DoctorManagementView.__init__` are now unused (they're still accepted as params but the factory passes lambdas that just trigger `_apply_filters()`). The callbacks are technically vestigial. | Simplify: remove the `on_search` and `on_filter` callbacks from `DoctorManagementView.__init__` since the view handles everything internally now. |
| ✅ PASS | No leftover mock controllers or placeholder implementations found. | No fix needed. |
| ✅ PASS | No `TODO`/`FIXME`/`HACK` comments found in the codebase (grep returned only `MAX_LOGIN_ATTEMPTS` config references). | No fix needed. |

### 3.2 Shared Component Usage

| Severity | Location | Issue | Suggested Fix |
|---|---|---|---|
| ✅ PASS | All list views (Users, Staff, Doctors, Departments, Appointments, Patients) | All use `BaseView` with `_enable_sorting`, `apply_default_sort`, and the shared sort-toggle logic. | No fix needed. |
| ✅ PASS | All date displays | All use `format_date()` / `format_datetime()` from `src/utils/formatters.py`. No ad-hoc `strftime` remaining. | No fix needed. |
| ✅ PASS | All validators | Patient registration, DOB, phone, email all use `src/utils/validators.py`. | No fix needed. |

### 3.3 Test Suite

| Metric | Value |
|---|---|
| Total test functions | 525 |
| Pass | 525 |
| Fail | 0 |
| Skip | 0 |
| Test files | 26 |
| Source files (non-init) | ~80 |

### 3.4 Test Coverage Gaps (Recently Added Features)

| Severity | Feature | Has Test? | Suggested Fix |
|---|---|---|---|
| 🟠 MAJOR | `src/gui/admin/reports_view.py` | ❌ No tests | Add basic smoke test: construct the view, verify widgets exist, verify generate callback fires. |
| 🟡 MINOR | `src/gui/common/about_view.py` | ❌ No tests | Add smoke test: construct with tkinter root, verify 3 team members + version label exist. |
| 🟡 MINOR | `src/utils/formatters.py` | ❌ No tests | Add unit tests for `format_date`, `format_datetime`, `parse_date_for_input` with various inputs (None, empty, date objects, datetime objects, string formats). |
| 🟡 MINOR | `src/gui/admin/doctor_management_view.py` | ✅ 6 tests | Covered (added in earlier fix). |
| ✅ PASS | Doctor filter (client-side) | ✅ | Covered in `test_doctor_management_view.py` test_client_side_filtering. |
| ✅ PASS | Date sort parsing (DD-MM-YYYY) | ✅ | Covered in `test_scheduling_engine.py` and `test_chart_widget.py`. |

---

## PART 4 — CODE QUALITY & IMPROVEMENT SUGGESTIONS

### 4.1 God-Object / Complexity Risk

| Severity | Location | Issue | Suggested Fix |
|---|---|---|---|
| 🔵 IMPROVEMENT | `src/gui/doctor/clinical_views.py` — **1,215 lines** | This single file contains `ClinicalRecordsView`, `PatientTimelineView`, `VisitFormView`, `VisitDetailView`, `PrescriptionFormDialog`, and `DocumentUploadDialog`. At 1,215 lines it's the largest file in the codebase and handles 6 distinct UI concerns. | Split into focused modules: `clinical_records.py` (list view), `patient_timeline.py` (timeline), `visit_forms.py` (create/edit visit), `visit_detail.py` (detail with tabs), `prescription_dialog.py`, `document_dialog.py`. |
| 🔵 IMPROVEMENT | `src/controllers/report_controller.py` — **524 lines** | The report controller has 16 RBAC-gated methods that are mostly thin dispatchers to `report_service`. The file has grown across multiple feature additions. | Split admin-report methods and doctor-dashboard methods into separate sections or classes. |
| 🔵 IMPROVEMENT | `src/services/scheduling_engine.py` — **641 lines** | Large but well-organized with clear internal helpers. Not urgent, but the `_check_day_schedule` method is complex (handles day-of-week, working hours, and lunch break in one method). | Could be split into `_check_day_of_week`, `_check_working_hours`, `_check_lunch` for clarity. Low priority. |

### 4.2 Error Handling Inconsistencies

| Severity | Location | Issue | Suggested Fix |
|---|---|---|---|
| 🔵 IMPROVEMENT | `src/gui/admin/chart_widget.py:55` + `src/gui/admin/analytics_dashboard_view.py:202,219,236...` | Broad `except Exception:` blocks that log and show a fallback. This is the correct approach for chart rendering (graceful degradation), but the pattern is inconsistent with the rest of the codebase where exceptions are more specifically caught. | Acceptable for charts. Document the pattern as intentional graceful-degradation for the matplotlib integration layer. |
| 🔵 IMPROVEMENT | `src/services/` vs `src/controllers/` | Services return `(success, message)` tuples. Controllers catch exceptions and also return `(success, message)`. But some controller methods also log exceptions while others don't. For example, `_handle_add_doctor` in `admin_factory.py` doesn't log on failure. | Standardize: all controller-level error handling should log + return + show messagebox. Create a helper if needed. |

### 4.3 Hardcoded Values → Config

| Severity | Location | Issue | Suggested Fix |
|---|---|---|---|
| 🟡 MINOR | `src/auth/remember_token.py:31` | `REMEMBER_DAYS = 14` is a hardcoded constant. Should be in `AppConfig` for configurability. | Move to `AppConfig.REMEMBER_ME_DAYS = int(os.getenv("REMEMBER_ME_DAYS", "14"))`. |
| 🟡 MINOR | `src/services/document_service.py:33` | `MAX_FILE_SIZE: int = 10 * 1024 * 1024` is hardcoded. Should be in `AppConfig`. | Move to `AppConfig.MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", str(10*1024*1024)))`. |
| 🟡 MINOR | `src/gui/main_window.py:156` | Clock tick interval `30000` (30 seconds) is hardcoded. Session timeout check frequency should be configurable or at least named. | Move to `AppConfig.CLOCK_TICK_MS = 30000`. |
| 🟡 MINOR | `src/database/seed_demo_data.py` | Doctor schedule data (working hours 09:00-17:00, lunch 12:00-13:00, slot_duration 15) are hardcoded. These are seed data so less critical, but named constants would improve clarity. | Create named constants at module level (e.g. `DEFAULT_WORK_START`, `DEFAULT_LUNCH_START`). |

### 4.4 Low-Effort, High-Value Additions

| Severity | Suggestion |
|---|---|
| 🔵 IMPROVEMENT | **Session refresh on user activity.** Currently, session timeout only checks on the 30-second clock tick. If the user is actively clicking buttons, the session should reset. Add `self._session_start = datetime.now()` in the `_on_navigate` handler. This is a one-line change that dramatically improves UX. |
| 🔵 IMPROVEMENT | **Test file for formatters.** `src/utils/formatters.py` has zero test coverage. Adding 10-15 unit tests for `format_date`, `format_datetime`, and `parse_date_for_input` would catch regressions from the date-format migration. |
| 🔵 IMPROVEMENT | **Test file for reports_view.** The reports module was recently rebuilt from broken code. A smoke test that constructs the view and verifies the generate callback would catch the same class of regression that broke it originally. |
| 🔵 IMPROVEMENT | **Export test coverage.** `src/services/export_service.py` (PDF/Excel export) has no dedicated test. A test that generates a small PDF and Excel file and verifies they're valid (e.g. file exists, size > 0, correct extension) would catch packaging/dependency issues. |
| 🔵 IMPROVEMENT | **Remove dead `filter_doctors` code.** Cleaning up the unused method in `doctor_controller.py` and `doctor_service.py` reduces confusion for the next developer. |

---

## 🏆 PRIORITIZED "FIX BEFORE PRESENTING" LIST

Ranked by **demo/evaluation risk** (what would an evaluator see or ask about), not just severity:

| # | Priority | Finding | Why It Matters for Demo |
|---|---|---|---|
| 1 | 🔴 **RBAC: Doctor-to-doctor access isolation** (Part 2.5) | `get_doctor_visits(doctor_id)` accepts any doctor ID — no ownership check. An evaluator asking "can Doctor A see Doctor B's records?" would get "yes" at the API level. | If the evaluator inspects the code or tests cross-role access, this looks like a security gap. The GUI doesn't expose it, but the code doesn't prevent it. |
| 2 | 🟠 **RBAC: Patient document access** (Part 2.5) | `DocumentController` methods accept any `patient_id` — a doctor can upload/view/delete docs for patients they haven't seen. | Same class of issue as #1. Quick to fix: add a doctor-patient association check. |
| 3 | 🟠 **No test for Reports view** (Part 3.4) | The reports module was recently rebuilt from completely broken code. No test coverage means a future regression could silently break it again. | If an evaluator clicks Reports and it crashes, that's a visible demo failure. |
| 4 | 🟡 **Dead `filter_doctors` code** (Part 3.1) | Code that does nothing but exists in controller+service. | Not a bug, but an evaluator doing a code review would wonder why it exists. |
| 5 | 🟡 **Session refresh on activity** (Part 4.4) | If a demo involves using the app for 30+ minutes, the session could expire mid-demo if the evaluator is slow. | One-line fix, high demo-reliability impact. |
| 6 | 🟡 **Scheduling engine docstring mismatch** (Part 2.1) | Docstring says 9 steps, implementation does 7. | Code review finding — looks sloppy. |
| 7 | 🔵 **clinical_views.py at 1,215 lines** (Part 4.1) | God-file risk. | Low demo risk but high maintainability signal for evaluators. |

---

**Summary:** The codebase is in solid shape for a capstone presentation. No 🔴 CRITICAL security holes (SQL injection, credential leaks, auth bypass) were found. The two 🟠 MAJOR findings are both in the RBAC isolation layer (doctor-to-doctor / doctor-to-patient access control), which are real but not exploitable through the current GUI. The main risks before presenting are: (1) the missing test coverage for the recently rebuilt Reports view, and (2) ensuring the session doesn't expire during a live demo.
