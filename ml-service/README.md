# FraudShield AI — Machine Learning Service

**FraudShield AI** is an intelligent credit card fraud detection and transaction risk monitoring system. This service provides a high-performance, modular, testable, and production-ready Python FastAPI microservice that performs leakage-safe feature preprocessing, probabilistic risk scoring, calibrated threshold classification, batch evaluation, and SHAP feature attribution explanations.

Designed as an independent microservice within a distributed architecture, it exposes a stable REST API designed for consumption by downstream backend services (e.g., Java Spring Boot) and operational monitoring dashboards.

---

## 1. Architecture & Directory Structure

```
ml-service/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application entrypoint & lifespan
│   ├── config.py                   # Pydantic Settings configuration
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── transaction.py          # Request schemas with strict validation
│   │   └── prediction.py           # Response models & risk categorization
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health.py           # /health endpoint (liveness/readiness)
│   │       └── predictions.py      # /internal/predict, /batch, /model-info
│   ├── services/
│   │   ├── __init__.py
│   │   ├── predictor.py            # Model inference, ordering & threshold logic
│   │   └── explanation.py          # SHAP TreeExplainer feature attributions
│   └── ml/
│       ├── __init__.py
│       ├── preprocessing.py        # RobustScaler on Time & Amount; passthrough V1-V28
│       └── model_loader.py         # Validated model artifact deserialization
├── training/
│   ├── __init__.py
│   ├── validate_data.py            # Comprehensive schema & data integrity checks
│   ├── eda.py                      # Exploratory data analysis & figure generator
│   ├── train.py                    # Baseline Logistic Regression pipeline
│   ├── evaluate.py                 # Metric calculations, PR curves & threshold tuning
│   └── compare_models.py           # Model tournament & final test set evaluation
├── tests/
│   ├── __init__.py
│   ├── test_health.py              # Health check & model-info tests
│   ├── test_predictions.py         # Single, batch, SHAP & edge case tests
│   └── test_schemas.py             # Schema boundary & NaN/inf rejection tests
├── artifacts/
│   └── fraud_model_v1.joblib       # Serialized winning pipeline bundle with metadata
├── reports/
│   ├── figures/                    # Confusion matrices, PR curves, and EDA plots
│   ├── data_validation_report.json # Dataset verification audit
│   ├── eda_summary.json            # Statistical distribution summaries
│   ├── eda_summary.md              # Markdown summary of EDA findings
│   ├── baseline_evaluation.json    # Baseline logistic regression results
│   ├── model_comparison.json       # Candidate models comparison metrics
│   └── model_comparison.md         # Markdown summary of comparison tournament
├── data/
│   └── raw/
│       └── creditcard.csv          # Transaction dataset (symlink / hardlink / local)
├── .env.example                    # Template environment variables
├── .env                            # Active environment configuration
├── .gitignore                      # Git exclusion rules
├── pyproject.toml                  # Ruff and Pytest settings
├── requirements.txt                # Pinned dependency requirements
├── Dockerfile                      # Non-root container image specification
├── .dockerignore                   # Build context exclusions
└── README.md                       # Comprehensive service documentation
```

---

## 2. Dataset Schema & Characteristics

The service is trained and validated on the publicly available **Credit Card Fraud Detection Dataset** (originating from European cardholders in September 2013).

- **Total Transactions:** 284,807 records
- **Class Imbalance:**
  - Legitimate (Class 0): 284,315 transactions (99.8273%)
  - Fraudulent (Class 1): 492 transactions (0.1727%)
  - Imbalance Ratio: **1 : 578**
- **Schema:**
  - `Time`: Seconds elapsed since the first transaction in the dataset (spans 48 hours / 172,792 seconds).
  - `V1` through `V28`: 28 numerical features derived from Principal Component Analysis (PCA) to protect user confidentiality.
  - `Amount`: Transaction monetary value (range: $0.00 to $25,691.16; median: $22.00).
  - `Class`: Binary ground truth target (0 = legitimate, 1 = fraudulent).

> **Important**: `Class` is strictly separated from inputs and is forbidden in inference payloads.

---

## 3. Leakage-Safe Machine Learning Methodology

1. **Chronological Time-Series Splitting:**
   - Rather than random cross-validation (which creates future lookahead data leakage in financial transaction streams), records are partitioned strictly by `Time`:
     - **Training Set (70%):** 199,364 transactions (384 frauds, 0.1926%)
     - **Validation Set (15%):** 42,721 transactions (56 frauds, 0.1311%)
     - **Test Set (15%):** 42,722 transactions (52 frauds, 0.1217%)
   - Every split contains sufficient fraud examples to calculate precise metrics.
2. **Preprocessing Isolation:**
   - Preprocessing (`RobustScaler` on `Time` and `Amount`) is fitted **strictly on the training partition**. PCA features `V1`–`V28` are preserved via passthrough.
3. **Threshold Optimization on Validation Data:**
   - The default threshold of 0.50 is suboptimal for imbalanced data. Decision thresholds are tuned on the validation set using F1-score maximization.
4. **Untouched Test Set Evaluation:**
   - The test set remains untouched during candidate selection and threshold tuning. The chosen model is evaluated only once on the test partition.

---

## 4. Empirical Evaluation Results

The model comparison tournament yielded the following reproducible results:

### Validation Set Comparison

| Model | Optimal Threshold | Val Precision | Val Recall | Val F1-Score | Val PR-AUC | Val ROC-AUC |
|---|---|---|---|---|---|---|
| **RandomForest** *(Selected)* | **0.5600** | **1.0000** | **0.7500** | **0.8571** | **0.8436** | **0.9846** |
| **XGBoost** | 0.8650 | 0.9773 | 0.7679 | 0.8600 | 0.8209 | 0.9855 |
| **Logistic Regression (Baseline)** | 0.9500 | 0.3551 | 0.8750 | 0.5052 | 0.8394 | 0.9828 |

### Model Selection Criteria & Decision Rationale

Although XGBoost achieved a marginally higher F1-score on the validation set (`0.8600` vs `0.8571`, difference of +0.0029), **Random Forest was deliberately chosen as the winning production model** based on three factors:

1. **Higher Precision-Recall Area Under Curve (PR-AUC):**
   - **Random Forest: `0.8436` vs. XGBoost: `0.8209`**
   - For heavily skewed fraud distributions (0.17% fraud rate), PR-AUC is the most reliable holistic metric. Random Forest demonstrated better average precision across operating thresholds.
2. **Prioritization of Fewer False Alarms (100% Validation Precision):**
   - **Random Forest: `1.0000` (0 False Positives on validation) vs. XGBoost: `0.9773` (1 False Positive)**
   - False positive alerts trigger merchant declines and costly manual compliance review. Random Forest minimized false alarms while maintaining competitive recall (75.0% vs 76.8%).
3. **Operating Threshold Stability:**
   - Random Forest peaked near a natural probability threshold (`0.5600`), whereas XGBoost required an extreme threshold of `0.8650` to suppress false alerts, making it more brittle to distribution shifts.

### Verification of Test Set Isolation (Zero Data Leakage)

- **Partition Separation:** Train (70%), Validation (15%), and Test (15%) were partitioned chronologically by `Time`.
- **Training Isolation:** All candidate models (Logistic Regression, Random Forest, XGBoost) and preprocessing pipelines were fitted exclusively on `X_train`.
- **Selection Isolation:** Threshold scanning and model comparison were conducted exclusively on `X_val`. The test set was **never accessed, queried, or used** during model selection.
- **Single Test Evaluation:** The test partition was evaluated **only once**, on the winning `RandomForest` model post-selection. Neither XGBoost nor Logistic Regression were ever evaluated on the test set.

### Final Test Set Results (Winning Model: `RandomForest` at Threshold = 0.5600)

Evaluated on 42,722 untouched transactions (52 actual fraud events):

- **Precision:** `0.8837` (38 out of 43 alerts were true fraud; only 5 false positives out of 42,670 legitimate transactions)
- **Recall:** `0.7308` (38 of 52 fraudulent attacks successfully caught)
- **F1-Score:** `0.8000`
- **PR-AUC (Average Precision):** `0.7661`
- **ROC-AUC:** `0.9611`

**Test Confusion Matrix:**
- True Negatives (TN): **42,665**
- False Positives (FP): **5**
- False Negatives (FN): **14**
- True Positives (TP): **38**

---

## 5. Quickstart & Installation (Windows & PowerShell)

### Prerequisites
- Python 3.11.x (verified on Python 3.11.9 64-bit)
- PowerShell 5.1+ or PowerShell Core

### Step 1: Navigate to Service Directory
```powershell
cd c:\Users\hp\Desktop\Projects\Ai_Mini_Project\ml-service
```

### Step 2: (Optional) Create and Activate Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Step 3: Install Pinned Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Create `.env` from template:
```powershell
Copy-Item .env.example .env
```

---

## 6. Execution Commands

### A. Run Dataset Integrity Validation
```powershell
python training/validate_data.py
```
Validates columns, non-finite values, NaN counts, duplicate analysis, and saves `reports/data_validation_report.json`.

### B. Run Exploratory Data Analysis (EDA)
```powershell
python training/eda.py
```
Generates 5 figures in `reports/figures/` and writes `reports/eda_summary.json` and `reports/eda_summary.md`.

### C. Train Baseline Model
```powershell
python training/train.py --save-artifact
```

### D. Run Model Tournament & Export Artifact
```powershell
python training/compare_models.py
```
Trains Logistic Regression, Random Forest, and XGBoost, selects the best model, evaluates it on the test partition, and saves `artifacts/fraud_model_v1.joblib`.

### E. Run Automated Tests
```powershell
pytest -v
```
Runs 24 automated tests covering health checks, single inference, batch prediction, Pydantic schemas, NaN/inf rejection, and SHAP explanations.

### F. Run Linter & Formatter
```powershell
ruff check .
ruff format .
```

---

## 7. Starting the FastAPI Server

Launch the ASGI server with Uvicorn:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The service will start at `http://127.0.0.1:8000`.

- **Interactive Swagger Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check Endpoint:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 8. API Specification & Examples

### Health Check: `GET /health`

**Response (200 OK):**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_version": "fraud-model-v1",
  "model_type": "RandomForest",
  "environment": "development"
}
```

---

### Model Info: `GET /internal/model-info`

**Response (200 OK):**
```json
{
  "model_version": "fraud-model-v1",
  "model_type": "RandomForest",
  "selected_threshold": 0.56,
  "expected_features": ["Time", "V1", ..., "V28", "Amount"],
  "training_dataset_description": "Credit Card Fraud Detection Dataset (284,807 transactions, 492 fraud cases)...",
  "risk_categories": {
    "LOW": "Score < 30.0 (Minimal risk, standard automated processing)",
    "MEDIUM": "Score 30.0 to 70.0 (Elevated risk, recommended secondary verification)",
    "HIGH": "Score >= 70.0 or above decision threshold (Actionable risk, flag for review/block)"
  }
}
```

---

### Single Transaction Prediction: `POST /internal/predict?explain=true`

**Sample Request Body:**
```json
{
  "Time": 406.0,
  "V1": -2.312,
  "V2": 1.951,
  "V3": -1.609,
  "V4": 3.997,
  "V5": -0.522,
  "V6": -1.426,
  "V7": -2.537,
  "V8": 1.391,
  "V9": -2.770,
  "V10": -2.772,
  "V11": 3.202,
  "V12": -2.899,
  "V13": -0.595,
  "V14": -4.289,
  "V15": 0.389,
  "V16": -1.140,
  "V17": -2.830,
  "V18": -0.016,
  "V19": 0.416,
  "V20": 0.126,
  "V21": 0.517,
  "V22": -0.035,
  "V23": -0.465,
  "V24": 0.320,
  "V25": 0.044,
  "V26": 0.177,
  "V27": 0.261,
  "V28": -0.143,
  "Amount": 0.0
}
```

**Sample Response Body (200 OK):**
```json
{
  "fraud_probability": 0.9994,
  "risk_score": 99.94,
  "predicted_class": 1,
  "risk_level": "HIGH",
  "threshold": 0.56,
  "model_version": "fraud-model-v1",
  "disclaimer": "Predictions represent estimated probabilistic risk score and do not constitute absolute determination of fraud.",
  "top_risk_factors": [
    {
      "feature": "V14",
      "attribution": 0.1463,
      "value": -4.289
    },
    {
      "feature": "V12",
      "attribution": 0.1049,
      "value": -2.899
    },
    {
      "feature": "V10",
      "attribution": 0.101,
      "value": -2.772
    },
    {
      "feature": "V4",
      "attribution": 0.0739,
      "value": 3.997
    },
    {
      "feature": "V17",
      "attribution": 0.0514,
      "value": -2.83
    }
  ]
}
```

---

### Batch Prediction: `POST /internal/predict/batch`

**Request Body:**
```json
{
  "transactions": [
    { "Time": 100.0, "V1": 0.1, ..., "V28": 0.0, "Amount": 15.00 },
    { "Time": 101.0, "V1": -3.2, ..., "V28": 0.5, "Amount": 240.00 }
  ]
}
```

**Response Body (200 OK):**
```json
{
  "total_transactions": 2,
  "flagged_fraud_count": 1,
  "model_version": "fraud-model-v1",
  "predictions": [
    {
      "fraud_probability": 0.02,
      "risk_score": 2.0,
      "predicted_class": 0,
      "risk_level": "LOW",
      "threshold": 0.56,
      "model_version": "fraud-model-v1",
      "disclaimer": "Predictions represent estimated probabilistic risk score and do not constitute absolute determination of fraud."
    },
    {
      "fraud_probability": 0.88,
      "risk_score": 88.0,
      "predicted_class": 1,
      "risk_level": "HIGH",
      "threshold": 0.56,
      "model_version": "fraud-model-v1",
      "disclaimer": "Predictions represent estimated probabilistic risk score and do not constitute absolute determination of fraud."
    }
  ]
}
```

---

## 9. Docker Deployment

### Build the Container Image
```bash
docker build -t fraudshield-ml-service:1.0.0 .
```

### Run the Container
```bash
docker run -d \
  --name fraudshield-ml \
  -p 8000:8000 \
  -e LOG_LEVEL=INFO \
  -e ENVIRONMENT=production \
  fraudshield-ml-service:1.0.0
```

### Mounting External Model Artifacts Dynamically
To swap or update the model artifact without rebuilding the image:
```bash
docker run -d \
  --name fraudshield-ml \
  -p 8000:8000 \
  -v $(pwd)/artifacts:/app/artifacts:ro \
  fraudshield-ml-service:1.0.0
```

---

## 10. Security & Operational Considerations

1. **Downstream Spring Boot Integration:**
   - The `/internal/*` routes are designed for service-to-service communication. In production, place this service in a private subnet or service mesh (e.g., behind Spring Cloud Gateway or an internal VPC), and enforce Mutual TLS (mTLS) or API Key authentication headers.
2. **Denial of Service Prevention:**
   - Batch requests are bounded by `MAX_BATCH_SIZE` (default: 500) to protect container memory from unbounded batch allocations.
3. **No Target Leakage:**
   - Any transaction payload containing `Class` is strictly rejected with `HTTP 422 Unprocessable Content`.
4. **Finite Numerical Enforcement:**
   - Inputs with `NaN`, `+Infinity`, or `-Infinity` are rejected before hitting the scikit-learn pipeline.
5. **PCA Feature Limitations:**
   - Features `V1`–`V28` are anonymized mathematical projections. The service explains them as numerical model features and does not invent speculative real-world meanings for them.

---

## 11. Change Log & Implementation History

This log records all development milestones, architectural decisions, technical fixes, and implemented components.

### Milestone 1: Workspace & Dataset Discovery
- **Action:** Inspected workspace directory `c:\Users\hp\Desktop\Projects\Ai_Mini_Project`.
- **Finding:** Found `data/raw/creditcard.csv` (150,828,752 bytes).
- **Architecture Decision:** Created `ml-service/` subproject to maintain microservice separation from upcoming Spring Boot (`backend/`) and React (`frontend/`).
- **Optimization:** Created an NTFS filesystem hardlink from `data/raw/creditcard.csv` to `ml-service/data/raw/creditcard.csv`, avoiding 150 MB duplicate disk usage while preserving zero-modification rules on user files.

### Milestone 2: Project Scaffolding & Configuration Architecture
- **Action:** Created modular directory layout adhering to clean separation of concerns:
  - `app/schemas/` (Pydantic v2 data models)
  - `app/api/routes/` (FastAPI route controllers)
  - `app/services/` (Business and prediction logic)
  - `app/ml/` (Preprocessors and model loading)
  - `training/` (Data validation, EDA, training, evaluation, comparison)
  - `tests/` (Unit and integration tests)
  - `artifacts/` (Serialized model bundles)
  - `reports/figures/` (Evaluation charts and diagnostic plots)
- **Action:** Authored `pyproject.toml`, `requirements.txt`, `.gitignore`, and `.env.example`.
- **Implementation:** Created `app/config.py` using `pydantic_settings.BaseSettings` with multi-path resolution (`resolve_dataset_path()`, `resolve_artifact_path()`).

### Milestone 3: Data Validation & Quality Verification (`training/validate_data.py`)
- **Implementation:** Built validation script auditing 31 columns, non-finite values, and label validity.
- **Audit Findings:**
  - 284,807 transactions (284,315 legitimate, 492 fraud; 0.1727% fraud rate).
  - 0 missing/null values across all columns.
  - 0 infinite/non-finite values.
  - 1,081 duplicate transactions (1,062 legitimate, 19 fraud) analyzed and cataloged.
- **Deliverable:** Saved audit report to `reports/data_validation_report.json`.

### Milestone 4: Exploratory Data Analysis & Visualizations (`training/eda.py`)
- **Implementation:** Implemented headless Matplotlib/Seaborn pipeline generating high-resolution diagnostic figures.
- **Deliverables Generated in `reports/figures/`:**
  - `class_distribution.png`: Linear and logarithmic imbalance comparison.
  - `amount_distribution.png`: Boxplot and KDE log-amount distributions showing fraudulent transactions have higher variance and a lower median than legitimate ones.
  - `time_distribution.png`: Transaction density across 48-hour timeline.
  - `feature_correlations.png`: Ranked Pearson correlations showing `V17`, `V14`, `V12`, `V10` have strongest negative correlation with fraud, while `V11` and `V4` have strongest positive correlation.
  - `selected_features_distribution.png`: Outlier-filtered boxplots comparing top discriminative features.
- **Summary Reports:** Written to `reports/eda_summary.json` and `reports/eda_summary.md`.

### Milestone 5: Leakage-Safe Machine Learning Pipeline (`training/train.py`, `app/ml/preprocessing.py`)
- **Implementation:** Built `get_feature_preprocessor()` with `ColumnTransformer` applying `RobustScaler` to `Time` and `Amount` and passing through `V1`–`V28`.
- **Time-Series Partitioning:** Enforced chronological splitting sorted strictly on `Time` (70% train, 15% val, 15% test).
- **Baseline Classifier:** Trained balanced Logistic Regression pipeline. Fitted preprocessor strictly on training data (`X_train`).
- **Deliverable:** Saved `reports/baseline_evaluation.json`, `reports/figures/confusion_matrix_baseline.png`, and `reports/figures/pr_curve_baseline.png`.

### Milestone 6: Model Comparison Tournament & Artifact Management (`training/compare_models.py`, `training/evaluate.py`)
- **Implementation:** Trained 3 candidate models on the training split:
  1. Balanced Logistic Regression (`solver='lbfgs'`, `max_iter=1000`)
  2. Balanced Random Forest (`n_estimators=100`, `max_depth=10`)
  3. Scaled XGBoost (`scale_pos_weight=518.18`, `n_estimators=150`, `max_depth=5`)
- **Threshold Tuning:** Evaluated candidates on validation set; scanned thresholds from 0.05 to 0.95 to optimize F1 score.
- **Winner Selection:** `RandomForest` won tournament with highest Validation PR-AUC (`0.8436`) and Validation F1 (`0.8571` at threshold `0.5600`).
- **Unbiased Test Set Evaluation:** Evaluated winning `RandomForest` on untouched test set (42,722 rows, 52 fraud cases):
  - Precision: `0.8837`
  - Recall: `0.7308`
  - F1-Score: `0.8000`
  - PR-AUC: `0.7661`
  - ROC-AUC: `0.9611`
  - Confusion Matrix: TN=42,665, FP=5, FN=14, TP=38
- **Artifact Serialization:** Exported pipeline and metadata bundle to `artifacts/fraud_model_v1.joblib`.
- **Comparison Reports:** Written to `reports/model_comparison.json` and `reports/model_comparison.md`.

### Milestone 7: Production FastAPI Application & Prediction Engine
- **Implementation:**
  - `app/schemas/transaction.py`: `TransactionInput` with strict `extra="forbid"` (rejecting `Class` and arbitrary fields) and finite number check.
  - `app/schemas/prediction.py`: `PredictionResponse`, `BatchPredictionResponse`, `HealthResponse`, `ModelInfoResponse`, and `RiskLevel` (`StrEnum`).
  - `app/ml/model_loader.py`: Deserialization validating required metadata keys and pipeline type.
  - `app/services/predictor.py`: Manages feature vector ordering, probability scoring, threshold evaluation, and batch evaluation.
  - `app/services/explanation.py`: Integrated SHAP `TreeExplainer` providing feature attributions with graceful fallback.
  - `app/api/routes/health.py`: `GET /health` reflecting model readiness.
  - `app/api/routes/predictions.py`: `GET /internal/model-info`, `POST /internal/predict`, `POST /internal/predict/batch`.
  - `app/main.py`: Lifespan event loader, CORS middleware, OpenAPI documentation.

### Milestone 8: Bug Fixes & Code Quality Hardening
- **Bug Fix 1 (Config Validation):** Fixed Pydantic v2 empty string parsing error for `DECISION_THRESHOLD_OVERRIDE` by adding a `@field_validator(mode="before")` pre-parsing empty strings to `None`.
- **Bug Fix 2 (Exception Serialization):** Resolved Starlette/FastAPI JSON encoding error when serializing Pydantic `RequestValidationError` containing Python `ValueError` objects in `ctx['error']` by using `fastapi.encoders.jsonable_encoder`.
- **Bug Fix 3 (Python 3.11 Enum Standard):** Migrated `RiskLevel(str, Enum)` to `RiskLevel(StrEnum)` conforming with PEP 663 / Ruff rule `UP042`.
- **Code Formatting:** Configured `pyproject.toml` with Ruff rules (`E`, `W`, `F`, `I`, `B`, `C4`, `UP`). Formatted entire codebase (`ruff check --fix .` and `ruff format .`).

### Milestone 9: Automated Test Suite (`tests/`)
- **Implementation:** Authored 24 automated test cases:
  - `tests/test_schemas.py` (10 tests)
  - `tests/test_health.py` (4 tests)
  - `tests/test_predictions.py` (10 tests)
- **Verification:** 100% test pass rate in 5.41s without requiring full dataset retraining.

### Milestone 10: Docker Containerization
- **Implementation:** Created multi-stage production `Dockerfile` with:
  - Base image: `python:3.11-slim`
  - Non-privileged runtime user (`appuser`, UID 10001)
  - Automated container healthcheck using `curl http://localhost:8000/health`
  - Dynamic volume mount support for model artifacts (`-v $(pwd)/artifacts:/app/artifacts:ro`)
- **Implementation:** Created `.dockerignore` excluding raw CSV datasets, tests, and temporary caches.

