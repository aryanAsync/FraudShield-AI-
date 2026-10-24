# FraudShield AI — Product Requirements Document (PRD) and Phase-Wise Implementation Plan

**Version:** 1.0  
**Status:** Implementation-ready draft  
**Product:** FraudShield AI — Credit Card Fraud Detection and Transaction Risk Monitoring System  
**Frontend:** React + TypeScript  
**Backend:** Unified FastAPI application (`ml-service/`)  
**Database:** PostgreSQL  
**ML:** Existing Random Forest artifact with optional SHAP explanations  
**Deployment:** Docker Compose for local development and demonstration

---

## 1. Executive Summary

FraudShield AI is a full-stack fraud-risk monitoring application. It accepts transaction features, scores each transaction using the existing machine-learning model, stores the transaction and prediction in PostgreSQL, presents risk signals to authorized users, and supports human investigation workflows.

The supplied handover reports that the ML inference service and PostgreSQL transaction persistence are implemented, with 44 automated tests passing. These are **reported current capabilities**, not independently verified facts; confirm them against the repository before extending it.

This PRD defines the target product, functional and non-functional requirements, proposed API and UI, data-model considerations, acceptance criteria, and a sequential implementation plan. The MVP is an academic/portfolio decision-support system, not a certified banking platform. Model predictions must not be represented as guaranteed truth.

## 2. Product Vision and Goals

### Goals
1. Deliver a working end-to-end flow: React → FastAPI → ML inference → PostgreSQL.
2. Preserve the existing model artifact, feature schema, preprocessing, threshold behavior, and prediction history.
3. Add secure authentication and server-side role-based access control.
4. Provide transaction review, alert triage, investigation cases, analytics, and auditability.
5. Make the app reproducible using environment configuration, migrations, tests, and Docker Compose.
6. Clearly communicate model limitations and distinguish predictions from human investigation outcomes.

### Non-goals for the MVP
- Processing real card payments or blocking transactions in a live payment network.
- Storing PAN, CVV, PIN, or other sensitive card authentication data.
- Claiming regulatory compliance or guaranteed fraud prevention.
- Automatically retraining the model from analyst decisions.
- Adding Kafka, Kubernetes, or distributed microservices without a demonstrated need.
- Adding a Spring Boot service; the agreed architecture is a unified FastAPI backend.
- Inventing real-world meanings for anonymized PCA features `V1`–`V28`.

## 3. Current State: Reported Baseline

The following is based on the supplied handover and should be verified against code and tests.

### 3.1 Reported ML capabilities
- Dataset: 284,807 records; features `Time`, `Amount`, and `V1`–`V28`; 492 fraud records (about 0.1727%).
- Validation/EDA/training/evaluation scripts and chronological train/validation/test split.
- Model artifact: `artifacts/fraud_model_v1.joblib`.
- Decision threshold: `0.5600`.
- Reported held-out test metrics: precision 0.8837, recall 0.7308, F1 0.8000, PR-AUC 0.7661, ROC-AUC 0.9611.
- SHAP explanations with fallback behavior.
- Reported routes: `GET /health`, `GET /internal/model-info`, `POST /internal/predict`, `POST /internal/predict/batch`.

### 3.2 Reported persistence capabilities
- SQLAlchemy 2.x, psycopg 3, Alembic, PostgreSQL.
- Tables/models: `transactions`, `predictions`, `investigation_cases`, `audit_logs`.
- Routes: `POST /api/v1/transactions/score`, `GET /api/v1/transactions`, `GET /api/v1/transactions/{id}`, `GET /api/v1/transactions/{id}/predictions`.
- Transaction and prediction intended to be persisted atomically.
- 44 automated tests reportedly passing.

### 3.3 Verify before new development
- PostgreSQL is running and `.env` points to the intended database.
- `alembic upgrade head` succeeds on a clean database.
- The current test suite passes in the actual checkout.
- Route prefixes and request/response schemas match this document.
- Case/audit models are not mistaken for complete case/audit workflows.
- `submitted_by`, `assigned_to`, and `actor_id` become proper user relationships when users are added.
- Internal prediction endpoints are not unintentionally exposed as public endpoints.
- Threshold overrides are permission-controlled and auditable.
- Duplicate external-reference/idempotency behavior is documented and tested.

### 3.4 Model interpretation and limitations
The reported test set has 52 fraud examples. At the reported recall of 0.7308, 38 of those fraud cases were detected and 14 were missed. The reported precision corresponds to 38 true positives and 5 false positives. These are offline results on a particular split, not guarantees of live performance.

`V1`–`V28` are anonymized PCA-derived features. Do not label them as merchant location, customer behavior, device data, or other real-world semantics without independent evidence. SHAP attribution describes model contribution, not proof of fraud or causation.

## 4. Users and Role Permissions

### Analyst
Can view transactions and prediction history, score transactions if policy permits, view explanations, open cases, add notes, and update cases assigned/accessible to them. Cannot manage users, assign administrator roles, or delete audit history.

### Administrator
Can do analyst actions, create/deactivate users, assign roles, review security/audit events, and view operational/model metadata. Cannot retrieve password hashes or modify/delete audit entries through ordinary application routes.

### Auditor
Read-only role recommended by the handover. Can inspect permitted transactions, predictions, cases, and audit logs, but cannot score transactions, modify cases, add notes, or manage users.

**MVP role set:** `ANALYST`, `ADMIN`, `AUDITOR`. If implementation must be staged, implement Analyst/Admin first while keeping the role model extensible for Auditor.

## 5. Functional Requirements

Priority: **P0** = MVP required; **P1** = important follow-up; **P2** = optional enhancement.

### FR-01 Authentication (P0)
- Login with normalized email and password.
- Store only a modern password hash; never plaintext passwords.
- Issue short-lived signed access tokens after successful authentication.
- Reject missing, malformed, expired, tampered, or invalid tokens.
- Reject inactive users at login and on protected routes.
- `GET /api/v1/auth/me` returns a safe user profile.
- Disable public self-registration by default.
- Create the first admin using a documented bootstrap CLI/script or controlled setup process.
- Never permit self-assignment of `ADMIN`.
- Never log passwords, hashes, signing secrets, or raw tokens.

Use a maintained password-hashing implementation (Argon2id preferred; bcrypt acceptable when deliberately configured) and a maintained JWT library. Do not implement cryptography manually.

### FR-02 Server-side RBAC (P0)
- Enforce permissions in FastAPI dependencies/services, not only in the UI.
- Create reusable current-user and role/permission dependencies.
- Protect scoring, case mutation, user administration, and audit endpoints.
- Return `401` for unauthenticated requests and `403` for insufficient permission.
- Test the role matrix on every protected route group.

### FR-03 Transaction scoring (P0)
- Validate payload against the model’s actual feature contract.
- Validate required numeric values, finite values, and applicable constraints such as non-negative amount.
- Call the existing ML service; do not duplicate model logic in React.
- Persist transaction and prediction atomically.
- Save probability, risk score, predicted class, risk tier, threshold, model version, and optional explanation.
- Return a stable response including transaction ID and prediction summary.
- Use actionable 4xx errors for invalid input; never expose stack traces.
- Restrict threshold overrides to authorized roles/configuration and audit every override.
- Define deterministic behavior for duplicate external references.

### FR-04 Transaction list, detail, and history (P0)
- Paginated transaction listing with risk-level and predicted-class filters.
- Add date and amount filters as P1.
- Use deterministic ordering and cap maximum page size.
- Detail endpoint returns feature values and latest prediction.
- Prediction history is append-only: rescoring creates a new prediction record.
- Validate query parameters and return 404 for missing records.

### FR-05 Explanations (P0)
- Show whether an explanation is available.
- Display top anonymized feature contributions and values.
- Explain that feature attribution is not proof of fraud or causality.
- Do not invent meanings for `V1`–`V28`.
- Prediction scoring should remain available if SHAP fails, if consistent with the existing service design.

### FR-06 Investigation case management (P0)
- Authorized analyst can create a case for a transaction requiring review.
- Enforce the current one-case-per-transaction rule unless intentionally changed.
- States: `OPEN`, `IN_REVIEW`, `CONFIRMED_FRAUD`, `LEGITIMATE`, `CLOSED`.
- Recommended transitions:
  - `OPEN` → `IN_REVIEW` or `CLOSED`
  - `IN_REVIEW` → `CONFIRMED_FRAUD`, `LEGITIMATE`, or `OPEN`
  - `CONFIRMED_FRAUD` → `CLOSED`
  - `LEGITIMATE` → `CLOSED`
  - `CLOSED` → terminal in MVP; reopening requires an explicit, audited action.
- Assign only to valid active analysts.
- Record status and assignment changes in audit logs.
- Prefer a `case_notes` table with author and timestamp for append-only notes. If retaining a single notes field, do not silently overwrite investigation history.
- Set and clear `resolved_at` consistently with permitted transitions.
- Enforce assignment/access rules if cases are restricted to assigned analysts.

### FR-07 Alert queue (P0)
- Surface HIGH-risk and predicted-fraud transactions for review.
- Sort by risk, prediction time, amount, and case status.
- Keep predicted fraud distinct from confirmed fraud.
- Include loading, empty, and error states.

### FR-08 Dashboard analytics (P0)
Provide:
- Total transactions scored.
- Predicted fraud count and predicted fraud rate.
- LOW/MEDIUM/HIGH distribution.
- Open and in-review case counts.
- Confirmed-fraud and legitimate outcomes from completed investigations.
- Recent transaction-scoring volume over time.
- Active model version and threshold.

Every metric must have a clear definition. Predicted fraud rate is not actual fraud prevalence. Outcome metrics must disclose reviewed/unknown counts where useful. Aggregate in PostgreSQL/backend rather than downloading all rows to the browser.

### FR-09 User administration (P0)
- Admin-only paginated user list.
- Admin can create users, change permitted roles, and deactivate/reactivate accounts.
- Never return password hashes.
- Prevent accidental deactivation of the last active admin where feasible.
- Normalize email case and enforce uniqueness.
- Audit user and role changes.

### FR-10 Audit trail (P0)
Audit login success/failure (without secrets), user creation/deactivation/role changes, scoring, threshold overrides, case creation/assignment/status changes/notes, and administrative settings changes.

Audit entries should include actor, action, entity, entity ID, timestamp, and limited structured metadata. Never log secrets, passwords, raw JWTs, or unnecessary raw transaction payloads. Do not expose audit update/delete routes. This is application-level immutability, not tamper-proof storage against a database administrator.

### FR-11 React frontend (P0)
Screens:
- Login.
- Authenticated app shell and role-aware navigation.
- Dashboard.
- Transactions table with filters/pagination.
- Transaction details with score, explanation, and prediction history.
- Alert queue.
- Investigation case list and workspace.
- Admin user management.
- Read-only audit screen for Admin/Auditor.
- Profile/logout and expired-session handling.

Use a typed API client and shared TypeScript types. The backend remains authoritative for validation and authorization. Never put model artifacts, database credentials, signing secrets, or privileged business logic in the frontend.

### FR-12 API consistency (P0)
- Versioned routes under `/api/v1`.
- Consistent JSON error shape and appropriate status codes.
- OpenAPI documentation kept accurate.
- Add request IDs/structured logging as P1.
- Never expose SQL, filesystem paths, environment values, or internal stack traces.

### FR-13 Deployment/configuration (P0 local, P1 production-like)
- Docker Compose starts PostgreSQL and FastAPI reproducibly.
- PostgreSQL uses a persistent named volume.
- Use Alembic for schema changes.
- Define health checks and service dependencies.
- Keep `.env.example` placeholders only; never commit `.env`.
- Do not expose PostgreSQL publicly by default.
- Document setup, migration, test, shutdown, and reset steps.

## 6. Non-Functional Requirements

### Security
- Modern password hashing, short-lived tokens, server-side RBAC, and secret management.
- Explicit CORS allowlist for frontend origins.
- SQLAlchemy parameterization; no user-built SQL strings.
- Validate input and return safe errors.
- Add login throttling/rate limiting before production-like deployment.
- HTTPS in deployed environments.
- Use synthetic/anonymized data; never collect sensitive card authentication information.
- Restrict internal inference endpoints to trusted use.

### Reliability and data integrity
- Transaction/prediction writes are atomic.
- Database constraints enforce invariants.
- Migrations work from an empty database and from the current schema.
- Missing database configuration/model artifacts fail clearly.
- Explanation failure does not necessarily fail scoring.
- Idempotency behavior is explicit.

### Performance
- Paginate list APIs and cap page sizes.
- Aggregate dashboard metrics in the database.
- Avoid loading the full dataset for ordinary requests.
- Configure pool sizes/timeouts for the actual environment.
- Establish performance targets only after measuring the running system.

### Accessibility and usability
- Risk labels must not rely on color alone.
- Forms, tables, status messages, and dialogs should be keyboard accessible.
- Use clear loading, empty, validation, permission, and server-error states.
- Separate model prediction from human investigation outcome throughout the UI.

### Maintainability
- Separate routes, schemas, services, repositories, models, and ML inference.
- Use type hints and Pydantic v2.
- Keep business logic out of React components.
- Add tests for new behavior and prevent regressions to the 44 reportedly passing tests.

## 7. Proposed API Contract

Verify existing route/schema names before implementing; preserve compatible routes where practical.

### Authentication and users
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout` only if token/session strategy gives it meaningful server-side behavior.
- `GET /api/v1/users` (Admin)
- `POST /api/v1/users` (Admin)
- `PATCH /api/v1/users/{user_id}` (Admin)

For stateless access tokens, logout usually means discarding the token client-side unless server-side revocation is implemented. Document the selected behavior.

### Transactions and model
- `POST /api/v1/transactions/score`
- `GET /api/v1/transactions`
- `GET /api/v1/transactions/{transaction_id}`
- `GET /api/v1/transactions/{transaction_id}/predictions`
- Keep `/internal/predict` and `/internal/predict/batch` restricted to trusted/internal use, not automatically public frontend APIs.

### Cases
- `GET /api/v1/cases`
- `POST /api/v1/cases`
- `GET /api/v1/cases/{case_id}`
- `PATCH /api/v1/cases/{case_id}` for allowed assignment/status changes.
- `POST /api/v1/cases/{case_id}/notes` if separate notes are implemented.
- Optional `GET /api/v1/transactions/{transaction_id}/case`.

### Analytics/audit
- `GET /api/v1/dashboard/summary`
- `GET /api/v1/dashboard/volume`
- `GET /api/v1/dashboard/risk-distribution`
- `GET /api/v1/audit-logs` (Admin/Auditor).

### Health/model info
- `GET /health`
- `GET /internal/model-info`, with access restricted as appropriate.

### API conventions
- ISO 8601 timestamps with timezone.
- Stable IDs and explicit field names.
- Pagination metadata such as `items`, `page`, `page_size`, `total`.
- `401` unauthenticated, `403` forbidden, `404` missing resource, `409` conflict, `422` validation failure.
- Response schemas must not serialize ORM models indiscriminately or reveal password hashes/secrets.

## 8. Data Model Requirements

### User model (new)
Fields: `id`, `name`, normalized unique `email`, `password_hash`, role (`ANALYST`, `ADMIN`, `AUDITOR`), `is_active`, `created_at`, `updated_at`, optional `last_login_at`.

Never include `password_hash` in response schemas.

### Existing relationships to review
- `transactions.submitted_by` → nullable FK to `users.id`.
- `investigation_cases.assigned_to` → nullable FK to `users.id`.
- `audit_logs.actor_id` → nullable FK to `users.id`.
- Prefer deactivation over deleting users so historical audit records remain meaningful.
- Choose FK deletion behavior to preserve audit and case history.
- Confirm `external_reference` uniqueness scope.
- Preserve prediction threshold, model version, and explanation snapshot.

### Case notes
Prefer a `case_notes` table with `id`, `case_id`, `author_id`, `body`, `created_at`; make notes append-only in MVP.

## 9. Frontend Information Architecture

### Navigation
Overview · Transactions · Alerts · Investigations · Audit Logs (Admin/Auditor) · User Management (Admin) · Profile/Logout.

### Screen requirements
- **Login:** email/password, validation, generic failure, loading state, no public admin registration.
- **Dashboard:** summary cards with definitions, risk distribution, scoring volume, case status, date filters.
- **Transactions:** server-side pagination/filter/sort and detail navigation.
- **Transaction detail:** amount, dataset transaction time, recorded time, model version, threshold, score, probability, class, history, and anonymized feature attribution.
- **Alerts:** triage list with risk, predicted class, date, case status, and assignment.
- **Investigation workspace:** case status, assignee, transaction summary, model explanation, notes/timeline, permitted actions.
- **User management:** admin-only list/create/update/deactivate; no password hashes.
- **Audit logs:** read-only, paginated, authorized view.

## 10. Phase-Wise Implementation Plan

Work on one phase at a time. After each phase, run tests, review diffs, and create a stable checkpoint.

### Phase 0 — Verify repository and environment
**Goal:** establish a known-good baseline.

Tasks:
1. Inspect README, repository tree, `.env.example`, `.gitignore`, Compose file, Alembic config/environment, settings, database session, models, routes, and tests.
2. Confirm Python version and active virtual environment.
3. Confirm PostgreSQL is running and the URL targets the intended database.
4. Run `alembic current`, then `alembic upgrade head` where appropriate.
5. Run the complete test suite and record exact results.
6. Start FastAPI and verify health, OpenAPI docs, and transaction endpoints.
7. Verify `.env` is ignored and no secrets are tracked.
8. Record any mismatch between the handover and repository.

**Exit criteria:** known-good startup instructions; migrations work; test baseline recorded; no secrets committed; no destructive reset.

### Phase 1 — Stabilize database and transaction APIs
**Goal:** dependable scoring and persistence.

Tasks:
1. Verify the payload contract against actual model input.
2. Test atomic transaction + prediction commit and rollback.
3. Define duplicate external-reference behavior and test it.
4. Verify list pagination, filters, deterministic ordering, detail 404, prediction history.
5. Test invalid inputs and database failures.
6. Verify migration from an empty database.
7. Ensure safe logs and typed responses.

**Exit criteria:** scoring is atomic; API schemas documented; persistence and route tests pass; existing model behavior is preserved.

### Phase 2 — Authentication, users, and RBAC
**Goal:** secure the backend before frontend integration.

Tasks:
1. Add User model and Alembic migration without deleting existing data.
2. Normalize email and enforce uniqueness; define role values.
3. Add password hashing and verification.
4. Add JWT creation/verification, configurable secret, and short token expiry.
5. Implement login and `/auth/me`.
6. Add secure first-admin bootstrap; no public admin registration.
7. Add `get_current_user` and reusable role/permission dependencies.
8. Protect scoring, write operations, and appropriate read endpoints.
9. Restrict internal routes or apply trusted-service/admin access.
10. Add admin user creation, role update, and deactivation.
11. Audit security events without logging credentials/tokens.
12. Configure explicit CORS origins and login throttling as appropriate.
13. Test missing, invalid, expired, tampered tokens; wrong password; inactive users; role restrictions.

**Exit criteria:** anonymous calls are rejected; role matrix works; secrets/hashes never leak; migrations preserve data; full tests pass.

**Token storage decision:** choose before React integration. HttpOnly/Secure/SameSite cookies can reduce JavaScript token theft but need deliberate CSRF protection. If bearer tokens are stored in browser storage for an academic demo, document the trade-off; localStorage is not equivalent to an HttpOnly cookie.

### Phase 3 — Investigation cases and alerts
**Goal:** enable human review of model alerts.

Tasks:
1. Add case schemas, repository/service layer, and routes.
2. Create cases from transactions and prevent duplicate cases.
3. Enforce state transitions in service logic.
4. Assign cases to valid active analysts.
5. Add append-only notes with author and timestamp.
6. Audit case creation, assignment, status changes, and notes.
7. Add filters by status, assignment, risk, predicted class, and date.
8. Test transitions, duplicate cases, authorization, and audit records.

**Exit criteria:** analyst can open/review/resolve/close cases; invalid transitions fail cleanly; notes and actions are traceable; model predictions remain separate from human outcomes.

### Phase 4 — Dashboard and analytics APIs
**Goal:** provide reliable aggregates.

Tasks:
1. Specify each metric and formula.
2. Add summary totals, predicted-fraud count/rate, risk distribution, and case counts.
3. Add volume-over-time endpoint with bounded date range and interval.
4. Add confirmed-outcome metrics from case outcomes.
5. Add paginated/filterable audit endpoint.
6. Aggregate in PostgreSQL and add indexes if needed.
7. Test empty database, date boundaries, timezone behavior, and fixture-based metric correctness.

**Exit criteria:** documented typed endpoints; no confusion between predicted and confirmed fraud; bounded queries; tests validate metrics.

### Phase 5 — React foundation and authentication
**Goal:** connect the UI securely to the API.

Tasks:
1. Create/verify React + TypeScript and routing.
2. Configure API base URL via frontend environment settings.
3. Add typed API client and shared request/response types.
4. Implement login, current-user loading, session expiry handling, and logout.
5. Add protected routes and role-aware navigation for usability; backend remains authoritative.
6. Add reusable layout, error handling, loading states, notifications, and form validation.
7. Configure CORS for the local frontend origin.
8. Test login success/failure, protected routes, and API failures.

**Exit criteria:** user logs in and loads `/auth/me`; expired sessions handled clearly; frontend/backend run concurrently; network requests reach correct API.

### Phase 6 — Transaction, alert, and investigation UI
**Goal:** complete the analyst workflow.

Tasks:
1. Build transaction table with server-side pagination, filters, and sorting.
2. Build transaction details and prediction history.
3. Show score, probability, predicted class, threshold, and model version consistently.
4. Render SHAP attribution with the anonymized-feature caveat.
5. Build alert queue and create-case action.
6. Build investigation workspace, notes, assignment, transitions, and confirmation dialogs.
7. Implement permission/validation/error/loading/empty states.
8. End-to-end test score → persist → alert → case → resolve.

**Exit criteria:** main workflow works through UI with persisted records; no mock data substitutes for integration; errors are understandable; case/audit updates are correct.

### Phase 7 — Dashboard, user management, and audit UI
**Goal:** finish admin and oversight features.

Tasks:
1. Build dashboard cards/charts from aggregate endpoints.
2. Label predicted and confirmed outcomes distinctly.
3. Build admin user list/create/update/deactivate screens.
4. Build read-only audit view for Admin/Auditor.
5. Add filters, pagination, empty states, and responsive behavior.
6. Test UI and direct API access for each role.
7. Perform basic accessibility checks.

**Exit criteria:** live dashboard; protected user management; auditor read-only behavior; metric definitions visible.

### Phase 8 — Docker, deployment readiness, and final QA
**Goal:** reproducible demonstration setup.

Tasks:
1. Review Dockerfiles and Compose dependencies/health checks.
2. Configure persistent PostgreSQL volume.
3. Configure secrets and service URLs via environment.
4. Add frontend service if useful; use container service DNS correctly.
5. Run migrations in a controlled deployment step.
6. Distinguish process health, model readiness, and database connectivity.
7. Run unit, integration, frontend, and end-to-end tests.
8. Test fresh checkout + empty database startup.
9. Add synthetic demo data and a repeatable demo script.
10. Document backup/reset steps.
11. Prepare architecture diagram, screenshots, API docs, model limitations, and README.

**Exit criteria:** reviewer can start the app from documentation; no committed secrets; data persists through restarts; migrations and tests pass.

### Optional Phase 9 — Enhancements (P2)
- CSV upload and batch scoring with file-size limits and per-row errors.
- Filtered CSV export.
- Model/version comparison view.
- Feedback and drift-monitoring reports.
- More advanced explanations.
- Background jobs for large batches.
- More production-grade observability/rate limiting.
- Streaming infrastructure only if justified by actual requirements.

## 11. Suggested Repository Structure

Keep the existing structure and adapt it; do not move files without a reason.

```text
Ai_Mini_Project/
├── docker-compose.yml
├── .gitignore
├── .env.example
├── ml-service/
│   ├── .env                    # local only; never commit
│   ├── alembic.ini
│   ├── alembic/versions/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── deps.py
│   │   │   └── routes/
│   │   │       ├── auth.py
│   │   │       ├── users.py
│   │   │       ├── transactions.py
│   │   │       ├── predictions.py
│   │   │       ├── cases.py
│   │   │       ├── dashboard.py
│   │   │       └── audit.py
│   │   ├── core/
│   │   │   ├── security.py
│   │   │   └── permissions.py
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   ├── session.py
│   │   │   ├── models/
│   │   │   └── repositories/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── ml/
│   ├── artifacts/
│   ├── training/
│   ├── tests/
│   └── requirements.txt
└── frontend/
    ├── package.json
    └── src/
        ├── api/
        ├── app/
        ├── components/
        ├── features/
        ├── hooks/
        ├── layouts/
        ├── pages/
        └── types/
```

This is a target layout, not a mandate to refactor the working ML service.

## 12. Testing and Acceptance

### Backend unit tests
- Password hash/verification, JWT validation, permission rules.
- Case transition rules.
- Metric calculations and query validation.
- Feature validation and SHAP fallback.

### Backend integration tests
- User migration/create/login/me/inactive rejection.
- Transaction persistence, rollback, and prediction history.
- Case lifecycle, assignment, notes, and audit events.
- Dashboard aggregates against known fixtures.
- User management and audit endpoint permissions.

### Frontend tests
- Login success/failure and session expiry.
- Protected routes and role navigation.
- Transaction filters/pagination/detail.
- Explanation rendering.
- Case transition confirmation and errors.
- Admin-only and auditor read-only screens.

### End-to-end acceptance scenario
1. Start PostgreSQL, FastAPI, and React using documented steps.
2. Log in as a seeded development analyst.
3. Score a synthetic transaction.
4. Verify transaction and prediction exist in PostgreSQL.
5. Find the record in transactions and dashboard.
6. Open a case, assign it, and add a note.
7. Move it through a permitted review outcome and close it.
8. Verify dashboard metrics update.
9. Verify audit entries exist for relevant actions.
10. Log in as Auditor and confirm read-only access.
11. Attempt admin operations as Analyst and confirm `403`.
12. Restart services and confirm data persists.
13. Run the full test suite.

**Release gate:** do not call the MVP complete until clean startup, critical authorization tests, all regression tests, documentation, and model limitations are verified.

## 13. Environment Configuration

Keep names aligned with actual settings. Suggested backend values:
- `DATABASE_URL`
- `JWT_SECRET_KEY` or equivalent
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `CORS_ORIGINS`
- `ENVIRONMENT`
- `MODEL_ARTIFACT_PATH` if configurable
- Controlled bootstrap-admin inputs/CLI options

Frontend:
- `VITE_API_BASE_URL` or equivalent.

Rules:
- `.env.example` contains placeholders only.
- Local `.env` is ignored by Git.
- No default production JWT secret.
- Fail clearly if required secrets are missing outside development.
- URL-encode reserved characters in database URLs.
- Never expose backend secrets through frontend environment variables.

## 14. Working with Antigravity / Coding Agents

For each phase:
1. Ask the agent to inspect the repository before editing.
2. Request a summary of existing behavior and tests.
3. Scope the task to one phase only.
4. Require migrations and data-preservation explanation before schema changes.
5. Implement models/schemas → services/repositories → routes/dependencies → tests → docs.
6. Run targeted tests and the full suite.
7. Review changed files and security implications.
8. Create a checkpoint/commit after acceptance.
9. Require an honest report of commands actually run and test results.

### Reusable phase prompt

```text
You are working on the existing FraudShield AI repository.

Before editing:
1. Inspect the repository and relevant files.
2. Summarize current implementation and tests.
3. Identify compatibility risks and propose a minimal plan.

Implement ONLY Phase [N]: [PHASE NAME] from the PRD.
Verify all claims against the actual code.

Constraints:
- Keep the unified FastAPI backend; do not add Spring Boot.
- Preserve the Random Forest artifact, feature schema, preprocessing,
  threshold behavior, transaction scoring, and prediction history unless
  a justified change is required and documented.
- Preserve existing data and use Alembic migrations for schema changes.
- Do not replace backend integration with mock data.
- Do not implement future phases in this task.
- Never commit or print secrets.
- Add tests for new behavior and regression tests for existing behavior.
- Do not claim tests passed unless you ran them.

At completion report:
1. Files changed and why.
2. Migration/configuration changes.
3. Exact commands run and actual test results.
4. Manual verification steps.
5. Known gaps and decisions needing approval.
```

## 15. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Migration damages existing data | Test upgrades on a copy and clean database; never drop data as a shortcut. |
| RBAC exists only in UI | Enforce and test authorization in backend dependencies/services. |
| Predictions presented as truth | Distinguish predicted class from human-confirmed case outcome. |
| Imbalanced data makes accuracy misleading | Report precision, recall, F1, PR-AUC, false positives/negatives, and test-set size. |
| PCA features get invented meanings | Display anonymized IDs and document limitations. |
| SHAP errors block scoring | Make explanations optional and report their availability. |
| Public registration creates admins | Disable public self-registration; use secure bootstrap. |
| Secrets leak | Ignore `.env`, use placeholders, redact logs, inspect Git status. |
| UI/API drift | Maintain OpenAPI schemas and typed frontend API types. |
| Misleading dashboard metrics | Define metrics and separate predicted from confirmed fraud. |
| Large queries slow the app | Pagination, database aggregates, bounded filters, and indexes. |
| Broad agent rewrite breaks working code | One phase per prompt, inspect diffs, test, checkpoint. |

## 16. Definition of Done

The MVP is complete when an authorized user can sign in, score a transaction, see its persisted prediction and explanation, review it in a transaction/alert interface, open and resolve an investigation case, and see updated dashboard metrics and audit events—all through React, FastAPI, and PostgreSQL.

Also required:
- Admin user management and Auditor read-only access work as specified.
- Migrations succeed on a fresh database.
- Docker Compose gives a reproducible local setup.
- Tests pass.
- README documents setup, architecture, API, model performance, limitations, and demo workflow.
- No unsupported claims of production readiness or guaranteed fraud prevention.

## 17. Immediate Next Steps

1. Verify PostgreSQL connectivity and current migration state.
2. Run the current backend tests and record the actual baseline.
3. Implement authentication, users, and RBAC before frontend work.
4. Review the User migration before applying it to the main development database.
5. Test all roles against direct API calls.
6. Implement case workflows, then analytics APIs.
7. Build React authentication and then transaction/alert/case workflows.
8. Finish dashboard/admin/audit UI and Docker clean-start testing.

**Phase numbering note:** The handover calls Authentication “Phase 3” because ML and database integration are already Phases 1 and 2. This PRD numbers baseline verification Phase 0 and stabilization Phase 1, so authentication is Phase 2 in this plan. Follow phase names rather than numbers if prompts use the original numbering.
