# FraudShield AI: Credit Card Fraud Detection and Transaction Risk Monitoring System

**FraudShield AI** is a production-grade financial risk monitoring and fraud detection system. The platform identifies, evaluates, flags, persists, and explains suspicious credit card transactions in real-time.

---

## 1. System Architecture

FastAPI serves as the unified application backend and inference engine, connecting directly to a React frontend and persisting all transactions and predictions in PostgreSQL:

```
React Frontend (Analyst & Admin Dashboard)
    |
    v [REST APIs]
FastAPI Application Backend (ml-service/)
    |
    |-- Authentication & Authorization (Upcoming phase)
    |-- Transaction APIs (/api/v1/transactions)
    |-- Machine Learning Prediction Service (Random Forest Pipeline)
    |-- Prediction History & Audit Logging
    |-- Dashboard & Analytics APIs (Upcoming phase)
    |-- Investigation Case Management (Upcoming phase)
    |
    v [SQLAlchemy 2.x & psycopg 3]
PostgreSQL Database (fraudshield)
```

- **`ml-service/`** *(FastAPI Backend & ML Engine)*: Core backend service handling data preprocessing, Random Forest inference, SHAP explainability, and PostgreSQL persistence with Alembic migrations.
- **`frontend/`** *(Upcoming Phase)*: React dashboard displaying live transaction feeds, fraud queues, risk distributions, and analyst investigation workflows.
- **`data/`**: Raw dataset (`creditcard.csv` with 284,807 transactions and 492 fraud cases).

---

## 2. Quick Start (Windows & PowerShell)

### Prerequisites
- Python 3.11.9
- PostgreSQL 16+ (or Docker for `docker-compose up -d postgres`)

```powershell
# 1. Start PostgreSQL (via Docker Compose or local Windows service)
docker compose up -d postgres

# 2. Navigate to backend / ML service
cd ml-service

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment (.env)
Copy-Item .env.example .env
# Set DATABASE_URL=postgresql+psycopg://postgres:your_password@localhost:5432/fraudshield

# 5. Run Alembic database migrations
alembic upgrade head

# 6. Run full test suite (44 passing tests)
pytest -v

# 7. Start FastAPI development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Swagger Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Endpoint:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **Score Endpoint:** `POST /api/v1/transactions/score`
- **Transactions API:** `GET /api/v1/transactions`

---

## 3. Project Implementation Milestones

| Phase | Milestone | Description & Key Results | Status |
|---|---|---|---|
| **Phase 1** | Machine Learning & EDA | Evaluated Logistic Regression, Random Forest, and XGBoost. Selected Random Forest (`PR-AUC: 0.8436`, `F1: 0.8571` on validation, `Precision: 0.8837` on test). Built FastAPI inference service with 24 baseline passing tests. | **Completed** |
| **Phase 2** | PostgreSQL Database Integration | Integrated SQLAlchemy 2.x, psycopg 3, and Alembic migrations. Created `transactions`, `predictions`, `investigation_cases`, and `audit_logs` tables. Added atomic scoring persistence and transaction history REST APIs. 44 passing tests. | **Completed** |
| **Phase 3** | Authentication & Security | JWT/OAuth2 analyst authentication, role-based access control (Analyst, Admin, Auditor), and protected routes. | Upcoming |
| **Phase 4** | Dashboard & Analytics APIs | Aggregate fraud metrics, daily velocity charts, risk tier distributions, and investigation case disposition queues. | Upcoming |
| **Phase 5** | React Analyst Frontend | Real-time transaction review UI, SHAP waterfall charts, alert triage, and manual fraud marking. | Upcoming |
