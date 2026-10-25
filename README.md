# FraudShield AI: Credit Card Fraud Detection and Transaction Risk Monitoring System

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI_0.115-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React_19_+_TypeScript-61DAFB.svg?logo=react)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL_16-336791.svg?logo=postgresql)](https://www.postgresql.org)
[![scikit-learn](https://img.shields.io/badge/ML-scikit--learn_RandomForest-F7931E.svg?logo=scikitlearn)](https://scikit-learn.org)
[![SHAP](https://img.shields.io/badge/Explainability-TreeExplainer_(SHAP)-blue.svg)](https://shap.readthedocs.io)
[![Backend Tests](https://img.shields.io/badge/Backend_Tests-111_Passed-brightgreen.svg)]()
[![Frontend Tests](https://img.shields.io/badge/Frontend_Tests-26_Passed-brightgreen.svg)]()

**FraudShield AI** is an enterprise-grade financial risk monitoring and fraud detection decision-support platform. The application provides end-to-end transaction scoring, vectorized batch CSV processing, real-time dynamic analytics, human investigation workflows, and explainable AI (SHAP) built on verified machine learning models and PostgreSQL persistence.

---

## 1. System Architecture

The system utilizes a unified FastAPI backend serving REST APIs and vectorized inference pipelines, connected to a modern React + TypeScript instrument panel frontend and PostgreSQL with ACID transaction guarantees:

```
┌────────────────────────────────────────────────────────────────────────┐
│             React + TypeScript Frontend (Vite, Port 5173)              │
│  • Executive Risk Overview    • CSV Batch Scoring & Validation         │
│  • Transaction Explorer       • Model Governance & Evaluation (Audit)  │
│  • Investigation Cases        • Role-Based Access Controls (RBAC)      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ REST API & Bearer JWT
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│             FastAPI Backend & ML Service (Uvicorn, Port 8000)          │
│  • Auth & RBAC (/api/v1/auth)       • Batch Scoring & History          │
│  • Preprocessing & RobustScaler    • Random Forest Inference Engine   │
│  • TreeExplainer SHAP Attributions  • Dynamic Analytics Aggregates    │
│  • Case State Machine Engine        • Immutable Audit Logging          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ SQLAlchemy 2.x & psycopg 3
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│             PostgreSQL 16 Relational Database (Port 5432)              │
│  • users (Analyst, Admin, Auditor)  • transactions (JSONB features)    │
│  • predictions (JSONB explanations) • investigation_cases & notes      │
│  • audit_logs (append-only)         • alembic_version (migrations)     │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Key Features & Implementation Highlights

### ⚡ CSV Batch Upload & Vectorized Inference
- **Drag-and-Drop File Upload:** Supports CSV files with up to 1,000 transactions (max 10 MB).
- **Client-Side Schema Validation:** Validates required feature columns (`Time`, `Amount`, `V1` through `V28`) and checks for non-negative values and finite numbers.
- **Ground-Truth Label Isolation:** Automatically detects any `Class` column (from datasets like Kaggle), displays an informational badge, and **strips the label from the inference payload** to prevent data leakage.
- **Atomic Persistence:** Transactions and model prediction records are persisted in a single PostgreSQL database transaction.
- **Instant Reconciled Summary:** Displays counts for total received, persisted, low-risk, medium-risk, high-risk, and flagged fraud.

### 📊 Real-Time Dynamic Analytics Dashboard
- **Live Database Telemetry:** Dashboard KPIs (Evaluated Transactions, Flagged Fraud, Average Risk Score, Pipeline Cases) are aggregated directly from PostgreSQL.
- **Automatic Invalidation:** TanStack React Query invalidates cached metrics after scoring, immediately updating the overview without manual page refreshes or counter hacks.
- **Time-Series Trends & Banding:** Visualizes risk distributions and inference volume by daily/hourly buckets.

### 🔍 Transaction Explorer & On-Demand SHAP Explainability
- **Search & Filtering:** Filter persisted transactions by ID, risk tier (`LOW`, `MEDIUM`, `HIGH`), and predicted class.
- **Detailed Feature Inspector:** Complete 30-feature vector inspection with one-click JSON copy.
- **On-Demand TreeExplainer:** If a transaction was scored in bulk without explanations, analysts can click **Generate SHAP Explanation** to calculate and persist top-10 feature attributions on demand.

### 🛡️ Model Governance & Evaluation
- **Verified Benchmark Reporting:** Dedicated `/model-evaluation` screen displaying verified test benchmarks from the held-out test split (42,722 transactions).
- **Interactive Confusion Matrix:** Visualizes True Negatives (`42,665`), False Positives (`5`), False Negatives (`14`), and True Positives (`38`).
- **Asymmetric Cost Rationale:** Explains the calibrated `0.5600` decision threshold under banking loss asymmetry (10.0x cost weight on missed fraud vs. 1.0x on false alarms).
- **Candidate Comparison Table:** Side-by-side comparison between deployed **Random Forest** and baseline **Logistic Regression** (with strict exclusion of unverified algorithms like XGBoost and Linear Regression).

### 📋 Investigation Workflow & State Machine
- **Alert Triage:** Open investigation cases directly from high-risk transaction detail cards.
- **Formal State Transitions:** Enforces valid lifecycle transitions: `OPEN` → `IN_REVIEW` → `CONFIRMED_FRAUD` / `LEGITIMATE` → `CLOSED`.
- **Analyst Notes & Audit Trail:** Case notes and status changes are permanently logged to `audit_logs`.

---

## 3. Verified Machine Learning Models

| Model | Deployment State | Decision Threshold | Test Precision | Test Recall | Test F1 | Test PR-AUC | Test ROC-AUC | Test Confusion Matrix |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Random Forest (`fraud-model-v1`)** | **PRODUCTION DEPLOYED** | **0.5600** | **0.8837** | **0.7308** | **0.8000** | **0.7661** | **0.9611** | TN: 42,665<br>FP: 5<br>FN: 14<br>TP: 38 |
| **Logistic Regression (`baseline-lr-v1`)** | **BASELINE ONLY (NOT DEPLOYED)** | 0.9500 | 0.3551 *(Val)* | 0.8750 *(Val)* | 0.5052 *(Val)* | 0.8394 *(Val)* | 0.9828 *(Val)* | *Not evaluated on test split* |

> [!NOTE]
> **Data Preprocessing Pipeline:** `RobustScaler` is fitted on `Time` and `Amount` (resilient to large monetary outliers), while PCA components `V1`–`V28` use passthrough identity mapping.

---

## 4. Full Setup Guide (For New Clones)

Follow these step-by-step instructions to run the entire application from scratch on your local machine.

### Prerequisites
- **Python:** 3.11+
- **Node.js:** 18+ (with `npm`)
- **PostgreSQL:** 16+ (Local service or Docker)
- **Git**

---

### Step 1: Clone the Repository
```bash
git clone https://github.com/aryanAsync/FraudShield-AI-.git
cd FraudShield-AI-
```

---

### Step 2: Start the PostgreSQL Database

#### Option A: Using Docker Compose (Recommended)
```bash
docker compose up -d postgres
```

#### Option B: Using Local PostgreSQL Service
Create a database named `fraudshield` owned by your PostgreSQL user:
```sql
CREATE DATABASE fraudshield;
```

---

### Step 3: Configure and Start Backend (`ml-service`)

1. **Create and activate a Python virtual environment:**
   ```bash
   # Windows PowerShell
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install Python dependencies:**
   ```bash
   cd ml-service
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   ```bash
   # Copy example environment configuration
   cp .env.example .env
   ```
   Open `.env` and configure your database connection string and secret key:
   ```ini
   DATABASE_URL=postgresql+psycopg://postgres:your_password@localhost:5432/fraudshield
   JWT_SECRET_KEY=your-super-secret-jwt-key-min-32-chars-long
   ACCESS_TOKEN_EXPIRE_MINUTES=480
   ENVIRONMENT=development
   LOG_LEVEL=INFO
   ENABLE_SHAP_EXPLANATIONS=true
   ```

4. **Apply database migrations:**
   ```bash
   alembic upgrade head
   ```

5. **Bootstrap seed users:**
   ```bash
   python scripts/bootstrap_admin.py --force --email admin@fraudshield.ai --password AdminSecurePass123! --name "Security Admin"
   ```

6. **Start the FastAPI server:**
   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   - API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   - Healthcheck: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

### Step 4: Configure and Start Frontend (`frontend`)

1. **Open a new terminal window** and navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. **Install frontend dependencies:**
   ```bash
   npm install
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   Ensure `.env` contains:
   ```ini
   VITE_API_BASE_URL=http://127.0.0.1:8000
   ```

4. **Start Vite development server:**
   ```bash
   npm run dev
   ```
   - Web Application: [http://localhost:5173](http://localhost:5173)

---

## 5. Seed Accounts & Roles

| Role | Email | Password | Permissions |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@fraudshield.ai` | `AdminSecurePass123!` | Full access: User management, model scoring, investigation cases, analytics, and audit logs. |
| **Risk Analyst** | `analyst@fraudshield.ai` | `AnalystSecurePass123!` | Score transactions, batch CSV uploads, open/resolve cases, add case notes, view analytics. |
| **Auditor** | `auditor@fraudshield.ai` | `AuditorSecurePass123!` | Read-only inspection: Review transactions, model evaluation, cases, and audit logs. |

---

## 6. How to Run the Demonstration Workflow

1. **Log in:** Open [http://localhost:5173/login](http://localhost:5173/login) and log in as `analyst@fraudshield.ai`.
2. **Review Dashboard:** Navigate to **Overview** (`/overview`) to view dynamic KPIs aggregated from PostgreSQL.
3. **Inspect Model Benchmarks:** Click **Model & Evaluation** (`/model-evaluation`) in the sidebar to review the deployed Random Forest test metrics (88.4% precision, 0.8000 F1) and interactive Confusion Matrix.
4. **Batch Score Transactions:**
   - Go to **Score Input** (`/score`).
   - Drag and drop [`sample_transactions_demo.csv`](sample_transactions_demo.csv) located in the repository root.
   - Note the green banner indicating the ground-truth `Class` label was detected and isolated.
   - Click **Score & Persist 50 Transactions**.
   - Review the reconciled batch results breakdown.
5. **Verify Dynamic Updates:** Click **View Executive Dashboard** and observe that all KPI counters and time-series charts updated from the newly persisted database records.
6. **Inspect SHAP Explainability:**
   - Go to **Transactions** (`/transactions`) and select a newly scored transaction.
   - Click **Generate SHAP Explanation** to compute and persist feature attributions using the TreeExplainer.

---

## 7. Testing & Quality Assurance

### Run Backend Tests (111 tests)
```bash
# In ml-service directory
pytest tests/ -v
```
All 111 tests pass covering authentication, RBAC, batch scoring, on-demand SHAP, model evaluation, migrations, schemas, case state machines, and audit logging.

### Run Frontend Tests & Checks (26 tests)
```bash
# In frontend directory
npm run test    # Vitest unit test suite (26 passing tests)
npm run lint    # Oxlint linter (0 errors, 0 warnings)
npm run build   # Production TypeScript & Vite build
```

---

## 8. Ethical & Decision-Support Notice

- **Decision-Support Only:** FraudShield AI is designed as an operational decision-support tool for fraud risk analysts. Predictions represent model estimates, not definitive legal or financial determinations of guilt.
- **Anonymized Features:** Features `V1` through `V28` are Principal Components from PCA transformation. They are not assigned artificial real-world semantics (e.g., merchant location or device fingerprints).
- **Explainability:** SHAP feature attributions reflect local additive mathematical contributions pushing the model probability toward (+) or away (-) from the decision threshold, and do not constitute independent proof of fraudulent activity.
