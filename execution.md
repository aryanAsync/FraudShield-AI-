# FraudShield AI — Phase-Wise Implementation & Execution Log

**Project:** FraudShield AI — Credit Card Fraud Detection and Transaction Risk Monitoring System  
**Repository:** `Ai_Mini_Project` / `ml-service`  
**Tracking Document:** `execution.md`  
**PRD Version:** 1.0 (`FraudShield_AI_PRD_and_Phase_Wise_Implementation.md`)  
**Backend:** Unified FastAPI (`ml-service/app/`)  
**Database:** PostgreSQL (`localhost:5432/fraudshield_db`)  
**ML Model:** Serialized Random Forest Classifier (`artifacts/fraud_model_v1.joblib`)  

---

## 1. Roadmap & Phase Progression Overview

| Phase # | Phase Name | Status | Verified Passing Tests | Alembic Migration |
|---|---|---|---|---|
| **Phase 0 & 1** | ML Model Inference & Database Persistence Baseline | ✅ Verified & Stable | 44 / 44 tests | `58a18413eb4f_create_core_tables.py` |
| **Phase 2** | Authentication, Users, and Server-Side RBAC | ✅ Verified & Stable | 62 / 62 tests | `9d65859ef4b9_create_users_table.py` |
| **Phase 3** | Investigation Case Management, Notes & Audit Trail APIs | ✅ Verified & Stable | 84 / 84 tests | `6f7bf46e53ab` & `9ef2bc4208d8` |
| **Phase 4** | Dashboard Analytics & Risk Aggregation APIs | ✅ **Audited & Verified** | **106 / 106 tests** | No schema drift (`9ef2bc4208d8`) |
| **Phase 5** | React + TypeScript Frontend Application | ⏳ Queued | Pending Phase 5 | N/A |
| **Phase 6** | Docker Compose Orchestration & Production Hardening | ⏳ Queued | Pending Phase 6 | N/A |

---

## 2. Phase 0 & Phase 1: Baseline Verification

### 2.1 Scope & Verification Summary
- **Baseline Capabilities:**
  - Machine learning inference pipeline wrapping `artifacts/fraud_model_v1.joblib` (Random Forest, threshold = `0.5600`).
  - Strict Pydantic v2 schemas validating 30 input features (`Time`, `Amount`, `V1`–`V28`).
  - Feature ordering integrity check preventing dataset drift.
  - Optional SHAP TreeExplainer attribution with graceful fallback.
  - PostgreSQL transaction persistence using SQLAlchemy 2.x and `psycopg 3`.
  - Atomic database transactions linking `transactions` and `predictions` records.
- **Verification Commands & Results:**
  - `python -m pytest -v`: **44 passed in 2.50s** (Python 3.11.9, pytest 9.1.1).
  - PostgreSQL database connectivity verified on `localhost:5432/fraudshield_db`.

---

## 3. Phase 2: Authentication, Users, and Server-Side RBAC

### 3.1 Executive Overview
Phase 2 implements enterprise-grade authentication, user lifecycle management, and server-side Role-Based Access Control (RBAC) following a zero-trust principle where permissions are strictly validated in FastAPI dependencies rather than relying on frontend client assertions.

### 3.2 Role Hierarchy & Permission Matrix

| Role | Scope | Permissions Implemented & Enforced |
|---|---|---|
| **`ADMIN`** | Full System Administration | User creation, role assignment, user activation/deactivation, audit review, model operational info, transaction scoring, case review. |
| **`ANALYST`** | Fraud Investigation & Scoring | Submit transactions for fraud evaluation (`POST /transactions/score`), view transactions, inspect SHAP explanations, view prediction history. Forbidden from accessing `/api/v1/users`. |
| **`AUDITOR`** | Read-Only Inspection | Inspect transactions, prediction evaluations, and audit logs. Strictly forbidden from triggering scoring (`403 Forbidden`) or modifying users (`403 Forbidden`). |

### 3.3 Database Architecture & Alembic Migration
- **Migration Script:** `alembic/versions/9d65859ef4b9_create_users_table.py`
- **Table Name:** `users`
- **Schema Details:**
  - `id` (INTEGER, Primary Key, autoincrement)
  - `name` (VARCHAR(128), Not Null)
  - `email` (VARCHAR(255), Not Null, Unique Index `ix_users_email`)
  - `password_hash` (VARCHAR(255), Not Null) — bcrypt salted hash
  - `role` (VARCHAR(32), Not Null, Default `'ANALYST'`)
  - `is_active` (BOOLEAN, Not Null, Default `TRUE`, Index `ix_users_is_active`)
  - `created_at` (TIMESTAMP WITH TIME ZONE, Server Default `NOW()`)
  - `updated_at` (TIMESTAMP WITH TIME ZONE, Server Default `NOW()`, onupdate)
  - `last_login_at` (TIMESTAMP WITH TIME ZONE, Nullable)
  - **Check Constraint:** `ck_users_role_valid` enforcing `role IN ('ANALYST', 'ADMIN', 'AUDITOR')`

### 3.4 Cryptography & Security Core (`app/core/security.py`)
- **Password Hashing:** `bcrypt` with automatic salt generation. Passwords are safe-sliced to 72 bytes to prevent Denial-of-Service attacks on bcrypt's internal byte limit.
- **JWT Signing:** `python-jose` generating HS256 signed access tokens with UTC timestamps (`iat`, `exp`), `sub` (normalized email), `user_id`, `role`, and `name`.
- **Security Protections:**
  - Password hashes are **never returned** by any endpoint.
  - Login failure responses use generic messages (`"Invalid email or password."`) to eliminate user enumeration vulnerabilities.
  - Deactivated accounts are blocked at login (`403 Forbidden`) and rejected immediately if presenting a previously issued token.

### 3.5 API Endpoints Implemented

#### Authentication (`/api/v1/auth`)
- `POST /api/v1/auth/login`: Authenticates email and password, verifies active status, updates `last_login_at`, records `AuditLog` event (`LOGIN_SUCCESS` or `LOGIN_FAILED`), and returns signed JWT access token.
- `GET /api/v1/auth/me`: Returns the safe profile of the currently authenticated active user.
- `POST /api/v1/auth/logout`: Records `AuditLog` event (`LOGOUT`) and confirms session termination.

#### User Administration (`/api/v1/users`) — *Admin Only*
- `GET /api/v1/users`: Paginated list of users with role and status filtering (`page`, `page_size`, `role`).
- `POST /api/v1/users`: Creates new user account with bcrypt hashing and records `USER_CREATED` audit event. Rejects duplicate emails with `409 Conflict`.
- `GET /api/v1/users/{id}`: Returns user details by ID.
- `PATCH /api/v1/users/{id}`: Updates user role, name, or active status. **Safety Guard:** Blocks deactivation or demotion of the last active administrator with `400 Bad Request`.

#### Transaction Route Protection (`/api/v1/transactions`)
- `POST /api/v1/transactions/score`: Protected by `require_analyst_or_admin`. Automatically falls back `submitted_by` to `current_user.email` if not provided. Auditors receive `403 Forbidden`; unauthenticated requests receive `401 Unauthorized`.
- `GET /api/v1/transactions`: Protected by `require_any_authenticated`.
- `GET /api/v1/transactions/{id}`: Protected by `require_any_authenticated`.
- `GET /api/v1/transactions/{id}/predictions`: Protected by `require_any_authenticated`.

### 3.6 Bootstrap CLI Script (`scripts/bootstrap_admin.py`)
- Idempotent administration utility:
  ```powershell
  python scripts/bootstrap_admin.py --email admin@fraudshield.ai --password "SecureAdminPassword2026!" --name "System Administrator"
  ```
- Creates the initial active administrator account if none exists, or safely skips if already provisioned. Logs audit event `BOOTSTRAP_ADMIN`.

### 3.7 Phase 2 Automated Test Suite
- Test file: `tests/test_auth_rbac.py`
- Test coverage includes:
  1. Password hashing & bcrypt 72-byte safe handling.
  2. JWT token generation, decoding, expiration rejection, and tampered signature rejection.
  3. User repository email case-normalization and `count_active_admins`.
  4. Database check constraints on user roles (`ck_users_role_valid`).
  5. Login flow success, wrong password rejection, non-existent email rejection, deactivated account rejection.
  6. Audit logging on login success, login failure, and logout.
  7. `GET /api/v1/auth/me` with valid, invalid, and missing tokens.
  8. Role enforcement matrix on `/api/v1/users` (Admin allowed, Analyst 403, Auditor 403, Unauthenticated 401).
  9. Admin user creation with duplicate email conflict prevention.
  10. Last-active-admin protection guard against deactivation and demotion.
  11. Transaction scoring RBAC enforcement (Analyst/Admin allowed, Auditor 403, Unauthenticated 401).
  12. Auditor read-only access verification on transaction list, details, and predictions.

---

## 4. Verification Logs & Command Outputs

### 4.1 Pytest Execution Log
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.7.0
rootdir: C:\Users\hp\Desktop\Projects\Ai_Mini_Project\ml-service
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.14.2
collected 62 items

tests/test_auth_rbac.py::test_password_hashing_and_verification PASSED   [  1%]
tests/test_auth_rbac.py::test_password_hashing_handles_long_passwords PASSED [  3%]
tests/test_auth_rbac.py::test_jwt_token_generation_and_decoding PASSED   [  4%]
tests/test_auth_rbac.py::test_jwt_token_expired_fails_decoding PASSED    [  6%]
tests/test_auth_rbac.py::test_jwt_token_tampered_signature_fails_decoding PASSED [  8%]
tests/test_auth_rbac.py::test_user_repository_email_normalization PASSED [  9%]
tests/test_auth_rbac.py::test_user_model_role_check_constraint PASSED    [ 11%]
tests/test_auth_rbac.py::test_count_active_admins PASSED                 [ 12%]
tests/test_auth_rbac.py::test_login_successful_flow PASSED               [ 14%]
tests/test_auth_rbac.py::test_login_invalid_password PASSED              [ 16%]
tests/test_auth_rbac.py::test_login_nonexistent_email PASSED             [ 17%]
tests/test_auth_rbac.py::test_login_deactivated_account_forbidden PASSED [ 19%]
tests/test_auth_rbac.py::test_auth_me_endpoint PASSED                    [ 20%]
tests/test_auth_rbac.py::test_logout_endpoint PASSED                     [ 22%]
tests/test_auth_rbac.py::test_user_management_role_enforcement PASSED    [ 24%]
tests/test_auth_rbac.py::test_admin_create_user PASSED                   [ 25%]
tests/test_auth_rbac.py::test_admin_cannot_deactivate_last_admin PASSED  [ 27%]
tests/test_auth_rbac.py::test_transaction_scoring_rbac PASSED            [ 29%]
tests/test_db_models.py::test_transaction_repository_create_and_get PASSED [ 30%]
tests/test_db_models.py::test_transaction_unique_external_reference PASSED [ 32%]
tests/test_db_models.py::test_transaction_prediction_atomic_link PASSED  [ 33%]
tests/test_db_models.py::test_multiple_predictions_history PASSED        [ 35%]
tests/test_cascade_delete_transaction_removes_predictions PASSED         [ 37%]
tests/test_prediction_check_constraints PASSED                          [ 38%]
tests/test_investigation_case_and_audit_log PASSED                      [ 40%]
tests/test_health.py::test_health_endpoint_healthy PASSED                [ 41%]
tests/test_health.py::test_health_endpoint_model_not_ready PASSED        [ 43%]
tests/test_health.py::test_model_info_endpoint PASSED                    [ 45%]
tests/test_health.py::test_model_info_service_unavailable PASSED         [ 46%]
tests/test_migrations.py::test_alembic_configuration_and_revisions PASSED [ 48%]
tests/test_migrations.py::test_metadata_contains_all_required_tables PASSED [ 50%]
tests/test_migrations.py::test_table_schema_integrity PASSED             [ 51%]
tests/test_predictions.py::test_predict_single_valid_transaction PASSED  [ 53%]
tests/test_predictions.py::test_predict_rejects_class_field PASSED       [ 54%]
tests/test_predictions.py::test_predict_rejects_missing_feature PASSED   [ 56%]
tests/test_predictions.py::test_predict_rejects_nan_and_inf PASSED       [ 58%]
tests/test_predictions.py::test_predict_threshold_override PASSED        [ 59%]
tests/test_predictions.py::test_predict_with_explanation PASSED          [ 61%]
tests/test_predictions.py::test_batch_prediction PASSED                  [ 62%]
tests/test_predictions.py::test_batch_prediction_exceeds_max_size PASSED [ 64%]
tests/test_predictions.py::test_missing_artifact_raises_clear_error PASSED [ 66%]
tests/test_predictions.py::test_consistent_feature_ordering PASSED       [ 67%]
tests/test_schemas.py::test_valid_transaction_schema PASSED              [ 69%]
tests/test_schemas.py::test_forbid_target_field_class PASSED             [ 70%]
tests/test_schemas.py::test_forbid_arbitrary_extra_fields PASSED         [ 72%]
tests/test_schemas.py::test_missing_feature_rejected PASSED              [ 74%]
tests/test_schemas.py::test_reject_nan_values PASSED                     [ 75%]
tests/test_schemas.py::test_reject_infinite_values PASSED                [ 77%]
tests/test_schemas.py::test_negative_amount_rejected PASSED              [ 79%]
tests/test_schemas.py::test_batch_transaction_empty_rejected PASSED      [ 80%]
tests/test_schemas.py::test_batch_transaction_valid PASSED               [ 82%]
tests/test_schemas.py::test_prediction_response_schema PASSED            [ 83%]
tests/test_transactions_api.py::test_score_and_persist_valid_transaction PASSED [ 85%]
tests/test_transactions_api.py::test_score_with_explanation PASSED       [ 87%]
tests/test_transactions_api.py::test_score_threshold_override PASSED     [ 88%]
tests/test_transactions_api.py::test_score_rejects_duplicate_external_reference PASSED [ 90%]
tests/test_transactions_api.py::test_score_rejects_class_and_extra_fields PASSED [ 91%]
tests/test_transactions_api.py::test_score_rejects_nan_and_inf PASSED    [ 93%]
tests/test_transactions_api.py::test_score_rollback_on_database_failure PASSED [ 95%]
tests/test_transactions_api.py::test_get_transaction_details_success_and_404 PASSED [ 96%]
tests/test_transactions_api.py::test_get_transaction_predictions_history PASSED [ 98%]
tests/test_transactions_api.py::test_list_transactions_pagination_and_filtering PASSED [100%]

======================= 62 passed, 8 warnings in 12.77s =======================
```

### 4.2 Linter & Code Quality Verification
```
ruff check .
All checks passed!
```

---

---

## 4. Phase 3: Investigation Case Management, Case Notes, and Audit Trail APIs

### 4.1 Executive Overview
Phase 3 builds the core investigative workflow for fraud analysts and compliance auditors. It transforms FraudShield AI from a pure scoring engine into a complete risk management platform where flagged transactions can be systematically triaged, assigned, investigated, annotated, and audited under strict server-side Role-Based Access Control (RBAC).

### 4.2 Database Architecture & Alembic Migrations
- **Migrations Applied:**
  1. `6f7bf46e53ab_create_case_notes_and_extend_cases.py`:
     - Creates the append-only `case_notes` relational table.
     - Adds `assigned_user_id` foreign key (`users.id` with `ON DELETE SET NULL`) to `investigation_cases`.
     - Adds `description` (`TEXT`, nullable) to `investigation_cases`.
     - Establishes indexes on `case_notes(case_id, created_at)` and `investigation_cases(assigned_user_id)`.
  2. `9ef2bc4208d8_add_cases_created_at_index.py`:
     - Adds descending sorting index `ix_investigation_cases_created_at_desc` on `investigation_cases.created_at`.
- **Relational Integrity:**
  - One-to-one constraint on `investigation_cases.transaction_id` prevents duplicate cases for the same transaction (`409 Conflict`).
  - Cascading deletes ensure deleting a test transaction cleans up its case and notes, but deactivating a user preserves all historical cases and note records via `ON DELETE SET NULL`.

### 4.3 Case State Machine & Status Lifecycle

The state machine strictly enforces valid status transitions in `CaseRepository.validate_status_transition`:

| Current Status | Permitted Next Statuses | Business Rationale & Metadata Action |
|---|---|---|
| `OPEN` | `IN_REVIEW`, `CLOSED` | Analyst claims or begins review; or triage marks case closed. |
| `IN_REVIEW` | `OPEN`, `CONFIRMED_FRAUD`, `LEGITIMATE` | Analyst sends back to queue, or adjudicates fraud/legitimate. Transitions to `CONFIRMED_FRAUD` or `LEGITIMATE` stamp `resolved_at = datetime.now(UTC)`. Transition to `OPEN` clears `resolved_at = None`. |
| `CONFIRMED_FRAUD` | `CLOSED` | Investigation complete; case archived as confirmed fraud. Resolution timestamp preserved. |
| `LEGITIMATE` | `CLOSED` | False positive resolved; case archived. Resolution timestamp preserved. |
| `CLOSED` | *None (Terminal)* | Closed cases are immutable. Reopening attempts return `422 Unprocessable Entity`. |

Any transition not explicitly permitted above is rejected with `422 Unprocessable Entity`. Direct jumps such as `OPEN` → `CONFIRMED_FRAUD` without analyst review are blocked.

### 4.4 Case Assignment Policy
- **Admin Assignment:** Administrators can assign any unassigned or assigned case to any active user possessing the `ANALYST` role.
- **Analyst Self-Claiming:** An analyst can claim an unassigned case (`assigned_user_id = current_user.id`).
- **Analyst Reassignment Prevention:** An analyst cannot reassign a case already assigned to another analyst (`403 Forbidden`).
- **Eligibility Validation:** Assigning cases to inactive users, auditors, administrators, or nonexistent user IDs is strictly rejected with `400 Bad Request`.
- **Auditor Restrictions:** Auditors have read-only access and cannot assign cases (`403 Forbidden`).

### 4.5 Chronological Append-Only Investigation Notes
- Stored in the dedicated `case_notes` relational table.
- Notes are strictly **append-only**: no `PUT`, `PATCH`, or `DELETE` endpoints exist.
- Author metadata (`author_id`, `author_name`, `author_email`, `author_role`) is derived securely from the authenticated JWT, preventing identity spoofing.
- Adding notes to a `CLOSED` case is forbidden (`422 Unprocessable Entity`).
- Empty or whitespace-only note bodies are rejected (`400` / `422`).
- Notes are retrieved in strictly deterministic chronological order (`created_at ASC, id ASC`).

### 4.6 Read-Only Audit Log API (`/api/v1/audit-logs`)
- Restricted strictly to `ADMIN` and `AUDITOR` roles; analysts receive `403 Forbidden`.
- Fully paginated (`page`, `page_size` with bounds `1 <= page_size <= 100`).
- Supports filtering by `actor_id`, `action`, `entity_type`, `entity_id`, `created_from`, and `created_to`.
- Enforces date validation: `created_from > created_to` returns `400 Bad Request`.
- Deterministic ordering: `created_at DESC, id DESC`.
- Immutable: all modification methods (`POST`, `PUT`, `PATCH`, `DELETE`) return `404` or `405 Method Not Allowed`.

### 4.7 Phase 3 API Contract Summary

| Method | Endpoint | Description | Allowed Roles | Error Responses |
|---|---|---|---|---|
| `GET` | `/api/v1/cases` | List and filter cases with role visibility rules | `ADMIN`, `ANALYST`, `AUDITOR` | 400, 401 |
| `POST` | `/api/v1/cases` | Open investigation case for a transaction | `ADMIN`, `ANALYST` | 401, 403, 404, 409 |
| `GET` | `/api/v1/cases/{case_id}` | Retrieve case details, transaction, prediction & notes | `ADMIN`, `ANALYST` (assigned/unassigned), `AUDITOR` | 401, 403, 404 |
| `PATCH` | `/api/v1/cases/{case_id}` | Update status, assign analyst, update description | `ADMIN`, `ANALYST` (self-claim / assigned) | 400, 401, 403, 404, 422 |
| `GET` | `/api/v1/cases/{case_id}/notes` | Retrieve chronological notes for a case | `ADMIN`, `ANALYST`, `AUDITOR` | 401, 403, 404 |
| `POST` | `/api/v1/cases/{case_id}/notes` | Add append-only investigation note | `ADMIN`, `ANALYST` (assigned/unassigned) | 400, 401, 403, 404, 422 |
| `GET` | `/api/v1/audit-logs` | Query and filter immutable audit trail | `ADMIN`, `AUDITOR` | 400, 401, 403 |

---

## 5. Verification Logs & Command Outputs

### 5.1 Pytest Execution Log (Full Test Suite)
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.7.0
rootdir: C:\Users\hp\Desktop\Projects\Ai_Mini_Project\ml-service
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 84 items

tests/test_auth_rbac.py::test_password_hashing_and_verification PASSED   [  1%]
tests/test_auth_rbac.py::test_password_hashing_handles_long_passwords PASSED [  2%]
tests/test_auth_rbac.py::test_jwt_token_generation_and_decoding PASSED   [  3%]
tests/test_auth_rbac.py::test_jwt_token_expired_fails_decoding PASSED    [  4%]
tests/test_auth_rbac.py::test_jwt_token_tampered_signature_fails_decoding PASSED [  5%]
tests/test_auth_rbac.py::test_user_repository_email_normalization PASSED [  7%]
tests/test_auth_rbac.py::test_user_model_role_check_constraint PASSED    [  8%]
tests/test_auth_rbac.py::test_count_active_admins PASSED                 [  9%]
tests/test_auth_rbac.py::test_login_successful_flow PASSED               [ 10%]
tests/test_auth_rbac.py::test_login_invalid_password PASSED              [ 11%]
tests/test_auth_rbac.py::test_login_nonexistent_email PASSED             [ 13%]
tests/test_auth_rbac.py::test_login_deactivated_account_forbidden PASSED [ 14%]
tests/test_auth_rbac.py::test_auth_me_endpoint PASSED                    [ 15%]
tests/test_auth_rbac.py::test_logout_endpoint PASSED                     [ 16%]
tests/test_auth_rbac.py::test_user_management_role_enforcement PASSED    [ 17%]
tests/test_auth_rbac.py::test_admin_create_user PASSED                   [ 19%]
tests/test_auth_rbac.py::test_admin_cannot_deactivate_last_admin PASSED  [ 20%]
tests/test_auth_rbac.py::test_transaction_scoring_rbac PASSED            [ 21%]
tests/test_cases_and_audit.py::test_admin_create_case_success PASSED     [ 22%]
tests/test_cases_and_audit.py::test_analyst_create_case_success PASSED   [ 23%]
tests/test_cases_and_audit.py::test_auditor_create_case_forbidden PASSED [ 25%]
tests/test_cases_and_audit.py::test_create_case_nonexistent_transaction_returns_404 PASSED [ 26%]
tests/test_cases_and_audit.py::test_create_duplicate_case_returns_409 PASSED [ 27%]
tests/test_cases_and_audit.py::test_case_listing_rbac_visibility PASSED  [ 28%]
tests/test_cases_and_audit.py::test_case_detail_forbidden_for_other_analyst PASSED [ 29%]
tests/test_cases_and_audit.py::test_case_list_date_range_validation PASSED [ 30%]
tests/test_cases_and_audit.py::test_admin_assign_case_success PASSED     [ 32%]
tests/test_cases_and_audit.py::test_analyst_claim_unassigned_case PASSED [ 33%]
tests/test_cases_and_audit.py::test_analyst_cannot_reassign_other_analyst_case PASSED [ 34%]
tests/test_cases_and_audit.py::test_assign_inactive_analyst_rejected PASSED [ 35%]
tests/test_cases_and_audit.py::test_assign_auditor_rejected PASSED       [ 36%]
tests/test_cases_and_audit.py::test_state_machine_valid_transitions PASSED [ 38%]
tests/test_cases_and_audit.py::test_state_machine_invalid_transition_returns_422 PASSED [ 39%]
tests/test_cases_and_audit.py::test_state_machine_terminal_closed_reopen_rejected PASSED [ 40%]
tests/test_cases_and_audit.py::test_add_case_note_and_chronological_listing PASSED [ 41%]
tests/test_cases_and_audit.py::test_cannot_add_note_to_closed_case PASSED [ 42%]
tests/test_cases_and_audit.py::test_audit_log_rbac_permissions PASSED    [ 44%]
tests/test_cases_and_audit.py::test_note_body_empty_or_whitespace_rejected PASSED [ 45%]
tests/test_cases_and_audit.py::test_note_and_audit_route_immutability PASSED [ 46%]
tests/test_cases_and_audit.py::test_audit_log_date_range_validation PASSED [ 47%]
tests/test_db_models.py::test_transaction_repository_create_and_get PASSED [ 48%]
tests/test_db_models.py::test_transaction_unique_external_reference PASSED [ 50%]
tests/test_db_models.py::test_transaction_prediction_atomic_link PASSED  [ 51%]
tests/test_db_models.py::test_multiple_predictions_history PASSED        [ 52%]
tests/test_db_models.py::test_cascade_delete_transaction_removes_predictions PASSED [ 53%]
tests/test_db_models.py::test_prediction_check_constraints PASSED        [ 54%]
tests/test_db_models.py::test_investigation_case_and_audit_log PASSED    [ 55%]
tests/test_health.py::test_health_endpoint_healthy PASSED                [ 57%]
tests/test_health.py::test_health_endpoint_model_not_ready PASSED        [ 58%]
tests/test_health.py::test_model_info_endpoint PASSED                    [ 59%]
tests/test_health.py::test_model_info_service_unavailable PASSED         [ 60%]
tests/test_migrations.py::test_alembic_configuration_and_revisions PASSED [ 61%]
tests/test_migrations.py::test_metadata_contains_all_required_tables PASSED [ 63%]
tests/test_migrations.py::test_table_schema_integrity PASSED             [ 64%]
tests/test_predictions.py::test_predict_single_valid_transaction PASSED  [ 65%]
tests/test_predictions.py::test_predict_rejects_class_field PASSED       [ 66%]
tests/test_predictions.py::test_predict_rejects_missing_feature PASSED   [ 67%]
tests/test_predictions.py::test_predict_rejects_nan_and_inf PASSED       [ 69%]
tests/test_predictions.py::test_predict_threshold_override PASSED        [ 70%]
tests/test_predictions.py::test_predict_with_explanation PASSED          [ 71%]
tests/test_predictions.py::test_batch_prediction PASSED                  [ 72%]
tests/test_predictions.py::test_batch_prediction_exceeds_max_size PASSED [ 73%]
tests/test_predictions.py::test_missing_artifact_raises_clear_error PASSED [ 75%]
tests/test_predictions.py::test_consistent_feature_ordering PASSED       [ 76%]
tests/test_schemas.py::test_valid_transaction_schema PASSED              [ 77%]
tests/test_schemas.py::test_forbid_target_field_class PASSED             [ 78%]
tests/test_schemas.py::test_forbid_arbitrary_extra_fields PASSED         [ 79%]
tests/test_schemas.py::test_missing_feature_rejected PASSED              [ 80%]
tests/test_schemas.py::test_reject_nan_values PASSED                     [ 82%]
tests/test_schemas.py::test_reject_infinite_values PASSED                [ 83%]
tests/test_schemas.py::test_negative_amount_rejected PASSED              [ 84%]
tests/test_schemas.py::test_batch_transaction_empty_rejected PASSED      [ 85%]
tests/test_schemas.py::test_batch_transaction_valid PASSED               [ 86%]
tests/test_schemas.py::test_prediction_response_schema PASSED            [ 88%]
tests/test_transactions_api.py::test_score_and_persist_valid_transaction PASSED [ 89%]
tests/test_transactions_api.py::test_score_with_explanation PASSED       [ 90%]
tests/test_transactions_api.py::test_score_threshold_override PASSED     [ 91%]
tests/test_transactions_api.py::test_score_rejects_duplicate_external_reference PASSED [ 92%]
tests/test_transactions_api.py::test_score_rejects_class_and_extra_fields PASSED [ 94%]
tests/test_transactions_api.py::test_score_rejects_nan_and_inf PASSED    [ 95%]
tests/test_transactions_api.py::test_score_rollback_on_database_failure PASSED [ 96%]
tests/test_transactions_api.py::test_get_transaction_details_success_and_404 PASSED [ 97%]
tests/test_transactions_api.py::test_get_transaction_predictions_history PASSED [ 98%]
tests/test_transactions_api.py::test_list_transactions_pagination_and_filtering PASSED [100%]

====================== 84 passed, 16 warnings in 23.53s =======================
```

### 5.2 Linter & Code Quality Verification
```
ruff check .
All checks passed!
```

### 5.3 Database Migration & Schema Drift Verification
```
alembic current
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
9ef2bc4208d8 (head)

alembic check
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
No new upgrade operations detected.
```

### 5.4 OpenAPI Schema Verification
```
Total Registered Paths: 17
Case & Audit Endpoints Registered:
  - /api/v1/cases (GET, POST)
  - /api/v1/cases/{case_id} (GET, PATCH)
  - /api/v1/cases/{case_id}/notes (GET, POST)
  - /api/v1/audit-logs (GET)
```

---

---

## 6. Phase 4: Dashboard Analytics & Risk Aggregation APIs

### 6.1 Executive Overview
Phase 4 implements a dedicated analytics and risk aggregation layer that serves production-ready summary metrics, distributions, time-series charts, and explainability insights directly to frontend consumers. All aggregations are performed efficiently at the database engine level (PostgreSQL) rather than calculating metrics in-memory or downloading raw rows.

### 6.2 Key Metric Definitions & Latest-Prediction Strategy
- **Distinct Transactions vs. Predictions vs. Cases:**
  - **Transaction (`total_transactions`):** Number of distinct transaction entities stored in the `transactions` table.
  - **Prediction (`total_predictions`):** Total model evaluation executions recorded in the `predictions` table (measures inference workload).
  - **Investigation Case (`total_cases`):** Independent workflow records tracked in `investigation_cases`.
- **Latest Prediction per Transaction Rule:**
  - To prevent double-counting transactions evaluated multiple times over their lifecycle, all current-state risk metrics (risk scores, fraud probabilities, risk tier distributions, and classification percentages) strictly use the **latest prediction per transaction**.
  - **Tie-Breaking Strategy:** Evaluated via a window function subquery:
    `ROW_NUMBER() OVER (PARTITION BY transaction_id ORDER BY predicted_at DESC, id DESC) AS rn WHERE rn = 1`.
- **Model-Predicted Fraud vs. Confirmed Fraud:**
  - `predicted_fraud_count` measures transactions whose latest ML model prediction generated `predicted_class = 1`.
  - `confirmed_fraud` strictly measures cases adjudicated as `CONFIRMED_FRAUD` by human analysts.
  - Unresolved cases (`OPEN`, `IN_REVIEW`) are explicitly distinguished and never mislabeled as confirmed outcomes.

### 6.3 Aggregation & SQL Architecture
- Aggregations are structured into targeted, non-Cartesian queries (`AnalyticsRepository`):
  1. Window function ranking query for latest predictions per transaction.
  2. Transaction volume and latest prediction conditional aggregations (`COUNT() FILTER(...)`, `AVG()`).
  3. Case status breakdown and average resolution time calculation (`EXTRACT(EPOCH FROM (resolved_at - created_at))`).
  4. Time-series bucket grouping using `date_trunc('hour'|'day', predicted_at)` in PostgreSQL with fallback to SQLite `strftime`.
  5. Top SHAP feature contribution ranking aggregated over a bounded sample (100 recent predictions) of stored JSONB explanations.
- Zero-data handling: All endpoints return valid schemas with clean zero counts, zero percentages, and empty lists rather than database exceptions.

### 6.4 API Endpoints Summary (`/api/v1/analytics`)

| Method | Endpoint | Purpose | Allowed Roles | Error Responses |
|---|---|---|---|---|
| `GET` | `/api/v1/analytics/overview` | Overall transaction volume, predictions, latest risk score, predicted fraud rate, and case counts | `ADMIN`, `ANALYST`, `AUDITOR` | 400, 401 |
| `GET` | `/api/v1/analytics/risk-distribution` | Risk tier counts (LOW, MEDIUM, HIGH) & classification split based on latest predictions | `ADMIN`, `ANALYST`, `AUDITOR` | 400, 401 |
| `GET` | `/api/v1/analytics/trends` | Time-series prediction volume, distinct transactions, and fraud rate grouped by hour or day | `ADMIN`, `ANALYST`, `AUDITOR` | 400, 401 |
| `GET` | `/api/v1/analytics/case-status-distribution` | Investigation status breakdown, assignment workload, and average resolution time (seconds) | `ADMIN`, `ANALYST`, `AUDITOR` | 400, 401 |
| `GET` | `/api/v1/analytics/feature-importance` | Mean absolute SHAP feature attributions ranked for high-risk predictions with AI disclaimer | `ADMIN`, `ANALYST`, `AUDITOR` | 400, 401 |

### 6.5 Role-Based Access Control
- All endpoints strictly require authentication (`require_any_authenticated`).
- Accessible to `ADMIN`, `ANALYST`, and `AUDITOR` roles (read-only analytics).
- Unauthenticated requests receive `401 Unauthorized`.
- Deactivated user accounts receive `403 Forbidden`.

---

## 7. Verification Logs & Command Outputs (Phase 4)

### 7.1 Pytest Execution Log (Full Test Suite — 101 Tests)
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.7.0
rootdir: C:\Users\hp\Desktop\Projects\Ai_Mini_Project\ml-service
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 101 items

tests/test_analytics.py::test_analytics_overview_empty_database PASSED   [  0%]
tests/test_analytics.py::test_analytics_overview_metrics_and_latest_prediction_rule PASSED [  1%]
tests/test_analytics.py::test_analytics_date_range_validation_bad_request PASSED [  2%]
tests/test_analytics.py::test_risk_distribution_breakdown PASSED         [  3%]
tests/test_analytics.py::test_risk_distribution_empty_dataset PASSED     [  4%]
tests/test_analytics.py::test_trends_daily_aggregation PASSED            [  5%]
tests/test_analytics.py::test_trends_invalid_interval_or_max_range_rejected PASSED [  6%]
tests/test_analytics.py::test_case_status_distribution_and_resolution_metrics PASSED [  7%]
tests/test_analytics.py::test_feature_importance_aggregation_success PASSED [  8%]
tests/test_analytics.py::test_feature_importance_missing_explanations_graceful_fallback PASSED [  9%]
tests/test_analytics.py::test_feature_importance_invalid_risk_level_rejected PASSED [ 10%]
tests/test_analytics.py::test_analytics_rbac_all_authenticated_roles_allowed PASSED [ 11%]
tests/test_analytics.py::test_analytics_unauthenticated_requests_return_401 PASSED [ 12%]
tests/test_analytics.py::test_analytics_deactivated_user_forbidden PASSED [ 13%]
tests/test_analytics.py::test_overview_date_filtering_precision PASSED   [ 14%]
tests/test_analytics.py::test_trends_hourly_aggregation PASSED           [ 15%]
tests/test_analytics.py::test_case_status_distribution_empty_database PASSED [ 16%]
tests/test_auth_rbac.py::test_password_hashing_and_verification PASSED   [ 17%]
tests/test_auth_rbac.py::test_password_hashing_handles_long_passwords PASSED [ 18%]
tests/test_auth_rbac.py::test_jwt_token_generation_and_decoding PASSED   [ 19%]
tests/test_auth_rbac.py::test_jwt_token_expired_fails_decoding PASSED    [ 20%]
tests/test_auth_rbac.py::test_jwt_token_tampered_signature_fails_decoding PASSED [ 21%]
tests/test_auth_rbac.py::test_user_repository_email_normalization PASSED [ 22%]
tests/test_auth_rbac.py::test_user_model_role_check_constraint PASSED    [ 23%]
tests/test_auth_rbac.py::test_count_active_admins PASSED                 [ 24%]
tests/test_auth_rbac.py::test_login_successful_flow PASSED               [ 25%]
tests/test_auth_rbac.py::test_login_invalid_password PASSED              [ 26%]
tests/test_auth_rbac.py::test_login_nonexistent_email PASSED             [ 27%]
tests/test_auth_rbac.py::test_login_deactivated_account_forbidden PASSED [ 28%]
tests/test_auth_rbac.py::test_auth_me_endpoint PASSED                    [ 29%]
tests/test_auth_rbac.py::test_logout_endpoint PASSED                     [ 30%]
tests/test_auth_rbac.py::test_user_management_role_enforcement PASSED    [ 31%]
tests/test_auth_rbac.py::test_admin_create_user PASSED                   [ 32%]
tests/test_auth_rbac.py::test_admin_cannot_deactivate_last_admin PASSED  [ 33%]
tests/test_auth_rbac.py::test_transaction_scoring_rbac PASSED            [ 34%]
tests/test_cases_and_audit.py::test_admin_create_case_success PASSED     [ 35%]
tests/test_cases_and_audit.py::test_analyst_create_case_success PASSED   [ 36%]
tests/test_cases_and_audit.py::test_auditor_create_case_forbidden PASSED [ 37%]
tests/test_cases_and_audit.py::test_create_case_nonexistent_transaction_returns_404 PASSED [ 38%]
tests/test_cases_and_audit.py::test_create_duplicate_case_returns_409 PASSED [ 39%]
tests/test_cases_and_audit.py::test_case_listing_rbac_visibility PASSED  [ 40%]
tests/test_cases_and_audit.py::test_case_detail_forbidden_for_other_analyst PASSED [ 41%]
tests/test_cases_and_audit.py::test_case_list_date_range_validation PASSED [ 42%]
tests/test_cases_and_audit.py::test_admin_assign_case_success PASSED     [ 43%]
tests/test_cases_and_audit.py::test_analyst_claim_unassigned_case PASSED [ 44%]
tests/test_cases_and_audit.py::test_analyst_cannot_reassign_other_analyst_case PASSED [ 45%]
tests/test_cases_and_audit.py::test_assign_inactive_analyst_rejected PASSED [ 46%]
tests/test_cases_and_audit.py::test_assign_auditor_rejected PASSED       [ 47%]
tests/test_cases_and_audit.py::test_state_machine_valid_transitions PASSED [ 48%]
tests/test_cases_and_audit.py::test_state_machine_invalid_transition_returns_422 PASSED [ 49%]
tests/test_cases_and_audit.py::test_state_machine_terminal_closed_reopen_rejected PASSED [ 50%]
tests/test_cases_and_audit.py::test_add_case_note_and_chronological_listing PASSED [ 51%]
tests/test_cases_and_audit.py::test_cannot_add_note_to_closed_case PASSED [ 52%]
tests/test_cases_and_audit.py::test_audit_log_rbac_permissions PASSED    [ 53%]
tests/test_cases_and_audit.py::test_note_body_empty_or_whitespace_rejected PASSED [ 54%]
tests/test_cases_and_audit.py::test_note_and_audit_route_immutability PASSED [ 55%]
tests/test_cases_and_audit.py::test_audit_log_date_range_validation PASSED [ 56%]
tests/test_db_models.py::test_transaction_repository_create_and_get PASSED [ 57%]
tests/test_db_models.py::test_transaction_unique_external_reference PASSED [ 58%]
tests/test_db_models.py::test_transaction_prediction_atomic_link PASSED  [ 59%]
tests/test_db_models.py::test_multiple_predictions_history PASSED        [ 60%]
tests/test_cascade_delete_transaction_removes_predictions PASSED         [ 61%]
tests/test_prediction_check_constraints PASSED                          [ 62%]
tests/test_investigation_case_and_audit_log PASSED                      [ 63%]
tests/test_health.py::test_health_endpoint_healthy PASSED                [ 64%]
tests/test_health.py::test_health_endpoint_model_not_ready PASSED        [ 65%]
tests/test_health.py::test_model_info_endpoint PASSED                    [ 66%]
tests/test_health.py::test_model_info_service_unavailable PASSED         [ 67%]
tests/test_migrations.py::test_alembic_configuration_and_revisions PASSED [ 68%]
tests/test_migrations.py::test_metadata_contains_all_required_tables PASSED [ 69%]
tests/test_migrations.py::test_table_schema_integrity PASSED             [ 70%]
tests/test_predictions.py::test_predict_single_valid_transaction PASSED  [ 71%]
tests/test_predictions.py::test_predict_rejects_class_field PASSED       [ 72%]
tests/test_predictions.py::test_predict_rejects_missing_feature PASSED   [ 73%]
tests/test_predictions.py::test_predict_rejects_nan_and_inf PASSED       [ 74%]
tests/test_predictions.py::test_predict_threshold_override PASSED        [ 75%]
tests/test_predictions.py::test_predict_with_explanation PASSED          [ 76%]
tests/test_predictions.py::test_batch_prediction PASSED                  [ 77%]
tests/test_predictions.py::test_batch_prediction_exceeds_max_size PASSED [ 78%]
tests/test_predictions.py::test_missing_artifact_raises_clear_error PASSED [ 79%]
tests/test_predictions.py::test_consistent_feature_ordering PASSED       [ 80%]
tests/test_schemas.py::test_valid_transaction_schema PASSED              [ 81%]
tests/test_schemas.py::test_forbid_target_field_class PASSED             [ 82%]
tests/test_schemas.py::test_forbid_arbitrary_extra_fields PASSED         [ 83%]
tests/test_schemas.py::test_missing_feature_rejected PASSED              [ 84%]
tests/test_schemas.py::test_reject_nan_values PASSED                     [ 85%]
tests/test_schemas.py::test_reject_infinite_values PASSED                [ 86%]
tests/test_schemas.py::test_negative_amount_rejected PASSED              [ 87%]
tests/test_schemas.py::test_batch_transaction_empty_rejected PASSED      [ 88%]
tests/test_schemas.py::test_batch_transaction_valid PASSED               [ 89%]
tests/test_schemas.py::test_prediction_response_schema PASSED            [ 90%]
tests/test_transactions_api.py::test_score_and_persist_valid_transaction PASSED [ 91%]
tests/test_transactions_api.py::test_score_with_explanation PASSED       [ 92%]
tests/test_transactions_api.py::test_score_threshold_override PASSED     [ 93%]
tests/test_transactions_api.py::test_score_rejects_duplicate_external_reference PASSED [ 94%]
tests/test_transactions_api.py::test_score_rejects_class_and_extra_fields PASSED [ 95%]
tests/test_transactions_api.py::test_score_rejects_nan_and_inf PASSED    [ 96%]
tests/test_transactions_api.py::test_score_rollback_on_database_failure PASSED [ 97%]
tests/test_transactions_api.py::test_get_transaction_details_success_and_404 PASSED [ 98%]
tests/test_transactions_api.py::test_get_transaction_predictions_history PASSED [ 99%]
tests/test_transactions_api.py::test_list_transactions_pagination_and_filtering PASSED [100%]

====================== 101 passed, 16 warnings in 29.64s ======================
```

### 7.2 Linter & Code Quality Verification
```
ruff check .
All checks passed!
```

### 7.3 Database Migration & Schema Parity Verification
```
alembic current
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
9ef2bc4208d8 (head)

alembic check
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
No new upgrade operations detected.
```

### 7.4 OpenAPI Schema Verification
```
Total Registered Paths: 22
New Analytics Endpoints Registered:
  - /api/v1/analytics/overview (GET)
  - /api/v1/analytics/risk-distribution (GET)
  - /api/v1/analytics/trends (GET)
  - /api/v1/analytics/case-status-distribution (GET)
  - /api/v1/analytics/feature-importance (GET)
```

### 7.5 Independent Final Verification Audit Findings
- **Audit 1 (Latest Prediction Correctness):** Confirmed `ROW_NUMBER() OVER (PARTITION BY transaction_id ORDER BY predicted_at DESC, id DESC) AS rn` strictly isolates newest inference per transaction before current-state aggregation. Trends endpoint counts raw evaluation events.
- **Audit 2 (Date & Timezone Semantics):** Identified and resolved Python `TypeError` risk when comparing offset-aware and offset-naive timestamps in `validate_date_range`. All inputs are now consistently normalized to UTC. Added boundary and timezone offset regression tests (`+05:30` IST and boundary equality).
- **Audit 3 (Investigation Outcome Undercounting):** Identified Phase 3 data-model limitation where `case.status` transitioning from `CONFIRMED_FRAUD` / `LEGITIMATE` to `CLOSED` overwrites status without an `adjudication_outcome` column, causing closed cases to be counted under `closed` rather than historical confirmed fraud. Formulated backward-compatible recommendation for future schema enhancement without breaking current migration contracts.
- **Audit 4 (Feature Importance Integrity):** Verified deterministic ordering (`predicted_at DESC, id DESC`), bounded sample size (100), mean absolute attribution calculation (`sum(abs(attr)) / count`), graceful handling of malformed/missing explanations, and presence of AI governance disclaimer.
- **Audit 5 (Metric Precision):** Verified separation of transaction, prediction, and case counts with zero join multiplication. Division by zero protected across all endpoints.
- **Audit 6 (Security & RBAC):** Verified `require_any_authenticated` on all 5 analytics routes; Admin, Analyst, Auditor granted access; unauthenticated (401) and deactivated (403) blocked.
- **Audit 7 (Test Verification):** 106 / 106 tests passing in 36.97s.

---

## 8. Next Steps — Phase 5: React + TypeScript Frontend Application
With Phase 4 audited, hardened, thoroughly tested (106/106 tests passing), and documented, the backend provides complete APIs for:
1. Authentication & RBAC (Admin, Analyst, Auditor).
2. Live transaction fraud scoring with SHAP feature attributions.
3. Full investigation case management, state machine transitions, and append-only notes.
4. Read-only system audit log exploration.
5. Executive dashboard analytics, risk distributions, trends, and feature importance.

The next milestone is **Phase 5: React + TypeScript Frontend Application**, which will build the user interfaces connecting to these production-ready endpoints.



