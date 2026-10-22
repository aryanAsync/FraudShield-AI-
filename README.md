# FraudShield AI: Credit Card Fraud Detection and Transaction Risk Monitoring System

**FraudShield AI** is a college mini-project implementing a modern, distributed financial risk monitoring and fraud detection system. The platform identifies, evaluates, flags, and explains suspicious credit card transactions in near-real-time.

---

## 1. Multi-Service Architecture

The system is planned and structured into three decoupled layers:

```
Ai_Mini_Project/
├── ml-service/                   # [COMPLETED] Python 3.11 & FastAPI Inference & ML Engine
├── backend/                      # [UPCOMING] Java Spring Boot Enterprise Business Logic & DB
├── frontend/                     # [UPCOMING] React Analyst & Admin Dashboard
├── data/
│   └── raw/
│       └── creditcard.csv        # Raw dataset (284,807 transactions, 492 fraud cases)
└── README.md                     # Root project overview & change log
```

- **`ml-service/`** *(Current Phase)*: Independent microservice handling data auditing, EDA, machine learning training, threshold calibration, REST inference, batch processing, and SHAP explainability.
- **`backend/`** *(Next Phase)*: Spring Boot service managing account state, cardholder records, transaction ingestion, and invoking `ml-service` via internal REST APIs.
- **`frontend/`** *(Final Phase)*: React UI displaying transaction streams, fraud alert queues, and risk score breakdowns.

---

## 2. Machine Learning Service Overview

For complete documentation, API specifications, and Docker deployment guides, refer to [`ml-service/README.md`](ml-service/README.md).

### Quick Commands (PowerShell)

```powershell
cd ml-service

# 1. Audit dataset schema & integrity
python training/validate_data.py

# 2. Generate Exploratory Data Analysis & visual reports
python training/eda.py

# 3. Train baseline Logistic Regression
python training/train.py --save-artifact

# 4. Run model tournament (LR, Random Forest, XGBoost) and save winning artifact
python training/compare_models.py

# 5. Execute 24 automated unit and integration tests
pytest -v

# 6. Start FastAPI inference server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Swagger Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Endpoint:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 3. Project Implementation Log & Changelog

This log documents all architectural milestones and implementations completed across the repository.

### Chronological Implementation Log

| Date / Milestone | Component | Description & Key Decisions | Status |
|---|---|---|---|
| **Phase 1** | Workspace Discovery | Located existing `creditcard.csv` in `data/raw/` (150 MB). Created NTFS hardlink to `ml-service/data/raw/creditcard.csv` for zero-copy file sharing. | **Completed** |
| **Phase 2** | Project Scaffolding | Established modular `ml-service/` structure, pinned `requirements.txt`, created `.env.example` and `app/config.py` with multi-path resolution. | **Completed** |
| **Phase 3** | Data Validation | Built `training/validate_data.py`. Confirmed 284,807 rows, 31 columns, 0 nulls, 0 non-finite values, 1,081 duplicates, and 492 fraud cases (0.1727%). | **Completed** |
| **Phase 4** | EDA & Reporting | Built `training/eda.py`. Generated 5 diagnostic figures in `reports/figures/` and published `reports/eda_summary.md`. | **Completed** |
| **Phase 5** | Baseline Training | Implemented `training/train.py` with chronological 70/15/15 time split. Fitted `RobustScaler` on train only. Optimized threshold on validation. | **Completed** |
| **Phase 6** | Model Comparison | Built `training/compare_models.py`. Evaluated Logistic Regression, Random Forest, and XGBoost on validation data. Selected `RandomForest` due to superior PR-AUC (`0.8436` vs `0.8209`), zero validation false alarms (`1.0000` precision), and threshold stability (`0.5600` vs `0.8650`), deliberately prioritizing fewer false alarms. Verified strict test set isolation (test partition was kept untouched during selection and evaluated only once post-selection: `Precision: 0.8837, Recall: 0.7308, F1: 0.8000, PR-AUC: 0.7661`). Exported `artifacts/fraud_model_v1.joblib`. | **Completed** |
| **Phase 7** | FastAPI Service | Developed `app/main.py`, `app/api/routes/`, `app/schemas/`, and `app/services/predictor.py`. Implemented single inference, bounded batch scoring, and SHAP `TreeExplainer` feature attributions. | **Completed** |
| **Phase 8** | Automated Testing | Implemented 24 automated tests in `tests/test_health.py`, `tests/test_predictions.py`, and `tests/test_schemas.py`. Reached 100% pass rate in 5.41s. | **Completed** |
| **Phase 9** | Production Docker | Created non-root `python:3.11-slim` `Dockerfile` with health checks and `.dockerignore`. Documented dynamic model volume mounts. | **Completed** |

---

## 4. Key Engineering Fixes Log

1. **Pydantic v2 Optional Float Override:** Handled empty string inputs for `DECISION_THRESHOLD_OVERRIDE` in `.env` using `@field_validator(mode="before")` to prevent validation crashes.
2. **FastAPI JSON Serialization of Validation Errors:** Replaced raw dictionary serialization in `RequestValidationError` with `fastapi.encoders.jsonable_encoder` to properly encode nested Python `ValueError` objects.
3. **Python 3.11 Type & Enum Standards:** Modernized schemas to use `enum.StrEnum` and standard type annotations (`dict`, `tuple`, `list`) following PEP 663 and Ruff linting standards.
4. **Resilient Explainability:** Designed SHAP `TreeExplainer` with defensive exception handling so explanation failures never block primary fraud scoring.
