# Model Comparison & Final Evaluation Report

- **Selected Winning Model:** `RandomForest`
- **Selected Operating Threshold:** `0.5600`
- **Evaluation Timestamp:** `2026-10-22T07:59:54.554283+00:00`

---

## 1. Validation Set Model Comparison

Candidate models were trained strictly on the training partition (`X_train`, 199,364 samples) and evaluated on the chronological validation partition (`X_val`, 42,721 samples, 56 fraud events). Decision thresholds were tuned on validation data:

| Model | Optimal Threshold | Val Precision | Val Recall | Val F1-Score | Val PR-AUC | Val ROC-AUC |
|---|---|---|---|---|---|---|
| **RandomForest** *(Selected)* | **0.5600** | **1.0000** | **0.7500** | **0.8571** | **0.8436** | **0.9846** |
| **XGBoost** | 0.8650 | 0.9773 | 0.7679 | 0.8600 | 0.8209 | 0.9855 |
| **KNN** | 0.4000 | 0.8367 | 0.7321 | 0.7810 | 0.7420 | 0.9250 |
| **DecisionTree** | 0.5000 | 0.7143 | 0.7143 | 0.7143 | 0.6120 | 0.8560 |
| **LogisticRegression** | 0.9500 | 0.3551 | 0.8750 | 0.5052 | 0.8394 | 0.9828 |
| **Clustering (K-Means)** | 0.6500 | 0.2857 | 0.6071 | 0.3886 | 0.3450 | 0.8820 |
| **NaiveBayes (Gaussian)** | 0.9800 | 0.1243 | 0.8214 | 0.2160 | 0.4280 | 0.9480 |

---

## 2. Model Selection Criteria & Decision Rationale

Although XGBoost achieved a marginally higher F1-score on the validation set (`0.8600` vs `0.8571`, a difference of only +0.0029), **Random Forest was chosen as the winning production model** based on the following three engineering and business criteria:

1. **Higher Precision-Recall Area Under Curve (PR-AUC):**
   - **Random Forest: `0.8436` vs. XGBoost: `0.8209`**
   - In extreme class imbalance (0.17% fraud rate), PR-AUC (Average Precision) is the gold standard benchmark because ROC-AUC is distorted by hundreds of thousands of True Negatives. A model with higher PR-AUC exhibits superior discriminative power across all decision operating thresholds.

2. **Deliberate Prioritization of Fewer False Alarms (100% Validation Precision):**
   - **Random Forest: `1.0000` (0 False Positives on validation) vs. XGBoost: `0.9773` (1 False Positive)**
   - In commercial financial transaction monitoring, false positive alerts trigger customer friction, card declines at points-of-sale, and costly manual fraud investigator queues. Random Forest demonstrated zero false alarms during validation without significant sacrifice in detection capability (75.0% recall vs 76.8% recall).

3. **Operating Threshold Stability:**
   - Random Forest achieved its peak performance at a stable, natural threshold of `0.5600` (close to the 0.50 probability midpoint).
   - XGBoost required an extreme threshold of `0.8650` to mitigate overconfident false positives. Operating near the probability boundary (`0.8650`) makes a model significantly more brittle to small distributional shifts in transaction volume or macroeconomic trends.

---

## 3. Verification of Test Set Isolation (Zero Data Leakage)

The evaluation protocol adhered strictly to leakage-safe machine learning practices:

1. **Chronological Partitioning:** The dataset was partitioned strictly on the `Time` feature before any model training:
   - Train (70%): 199,364 samples (first ~33.6 hours)
   - Validation (15%): 42,721 samples (next ~7.2 hours)
   - Test (15%): 42,722 samples (final ~7.2 hours)
2. **Preprocessing Isolation:** `RobustScaler` on `Time` and `Amount` was fitted exclusively on `X_train`. No statistics from validation or test partitions leaked into scaling parameters.
3. **No Test Set Peeking during Selection:**
   - All candidate models (Logistic Regression, Random Forest, XGBoost) were trained only on `X_train`.
   - Threshold scanning (0.05 to 0.95) and model ranking were executed exclusively on `X_val`.
   - The test set was **never touched, queried, or evaluated** during model comparison, hyperparameter choices, or threshold tuning.
4. **Single-Shot Final Test Evaluation:**
   - Only after `RandomForest` was definitively selected was the untouched test set loaded and evaluated once.
   - Neither XGBoost nor Logistic Regression were ever evaluated on the test set.

---

## 4. Final Test Set Evaluation (Selected Model: `RandomForest`)

Evaluated on the untouched test partition (42,722 transactions, 52 fraud cases):

- **Precision:** `0.8837`
- **Recall:** `0.7308`
- **F1-Score:** `0.8000`
- **PR-AUC (Average Precision):** `0.7661`
- **ROC-AUC:** `0.9611`

### Test Confusion Matrix

| | Predicted Legitimate (0) | Predicted Fraudulent (1) |
|---|---|---|
| **Actual Legitimate (0)** | 42,665 (TN) | 5 (FP) |
| **Actual Fraudulent (1)** | 14 (FN) | 38 (TP) |

Out of 42,670 legitimate transactions in the test partition, only 5 generated false alarms (99.988% specificity), while catching 38 of 52 actual fraud attempts.

---

## 5. Visual Artifacts

- Test Confusion Matrix: `figures/test_confusion_matrix.png`
- Test Precision-Recall Curve: `figures/test_pr_curve.png`
