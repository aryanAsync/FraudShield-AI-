# Exploratory Data Analysis (EDA) Summary

## 1. Class Imbalance
- **Total Transactions:** 284,807
- **Legitimate Transactions (0):** 284,315 (99.83%)
- **Fraudulent Transactions (1):** 492 (0.1727%)
- **Imbalance Ratio:** 1:578

## 2. Amount Distribution
| Metric | Legitimate ($) | Fraudulent ($) |
|---|---|---|
| mean | 88.29 | 122.21 |
| std | 250.11 | 256.68 |
| min | 0.0 | 0.0 |
| 25% | 5.65 | 1.0 |
| 50% | 22.0 | 9.25 |
| 75% | 77.05 | 105.89 |
| max | 25691.16 | 2125.87 |

## 3. Top Predictive Features (Correlation with Class)
### Strongest Negative Correlation (Lower value -> Higher fraud risk):
- **V17**: -0.3265
- **V14**: -0.3025
- **V12**: -0.2606
- **V10**: -0.2169
- **V16**: -0.1965

### Strongest Positive Correlation (Higher value -> Higher fraud risk):
- **V11**: 0.1549
- **V4**: 0.1334
- **V2**: 0.0913
- **V21**: 0.0404
- **V19**: 0.0348

## 4. Visualizations Generated
- `figures/class_distribution.png`
- `figures/amount_distribution.png`
- `figures/time_distribution.png`
- `figures/feature_correlations.png`
- `figures/selected_features_distribution.png`
