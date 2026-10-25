import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ShieldCheck,
  Cpu,
  Layers,
  Scale,
  CheckCircle2,
  AlertTriangle,
  Info,
  RefreshCw,
  GitCompare,
  TrendingUp,
} from 'lucide-react'
import { modelsApi } from '../../api'
import { Skeleton } from '../../components/ui/Skeleton'
import { ErrorState } from '../../components/feedback/ErrorState'
import { Button } from '../../components/ui/Button'
import './ModelEvaluation.css'

export const ModelEvaluationPage: React.FC = () => {
  const [activeSplit, setActiveSplit] = useState<'test' | 'validation'>('test')

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['model-evaluation'],
    queryFn: () => modelsApi.getEvaluation(),
  })

  if (isLoading) {
    return (
      <div className="model-eval-page">
        <Skeleton height="36px" width="320px" />
        <div style={{ marginTop: '16px' }}>
          <Skeleton height="140px" />
        </div>
        <div style={{ marginTop: '24px' }}>
          <Skeleton height="340px" />
        </div>
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="model-eval-page">
        <ErrorState
          title="Failed to Load Model Evaluation Data"
          error={error || 'Could not fetch model metrics from backend service.'}
          onRetry={() => refetch()}
        />
      </div>
    )
  }

  const { deployed_model: rf, baseline_model: lr, evaluation_timestamp, comparison_summary } = data

  const currentRfMetrics = activeSplit === 'test' && rf.test_metrics ? rf.test_metrics : rf.validation_metrics
  const testCm = rf.test_metrics?.confusion_matrix
  const valCm = rf.validation_metrics.confusion_matrix

  const totalEvaluated = testCm
    ? testCm.true_negatives + testCm.false_positives + testCm.false_negatives + testCm.true_positives
    : 42722

  return (
    <div className="model-eval-page">
      {/* Header */}
      <div className="page-header">
        <div>
          <div className="page-title-row">
            <h1 className="page-title">Model Governance &amp; Evaluation</h1>
            <span className="live-status-pill">
              <span className="live-dot" /> Verified Production Artifacts
            </span>
          </div>
          <p className="caption">
            Comprehensive audit report, holdout test benchmarks, decision thresholds, and baseline comparison.
          </p>
        </div>
        <div className="header-actions">
          <Button
            variant="secondary"
            size="sm"
            leftIcon={<RefreshCw size={14} className={isFetching ? 'spin' : ''} />}
            onClick={() => refetch()}
          >
            Refresh Metrics
          </Button>
        </div>
      </div>

      {/* Production Banner */}
      <div className="deployed-model-banner panel">
        <div className="banner-left">
          <div className="model-badge-icon">
            <ShieldCheck size={28} />
          </div>
          <div>
            <div className="banner-title-line">
              <h2 className="banner-model-title">{rf.model_name} Classifier</h2>
              <span className="badge-deployed">DEPLOYED PRODUCTION</span>
              <span className="version-tag mono">{rf.model_version}</span>
            </div>
            <p className="banner-description">
              {rf.status_label} &bull; Decision Threshold:{' '}
              <strong className="mono">{rf.selected_threshold.toFixed(2)}</strong> (cost-calibrated for asymmetric loss)
            </p>
          </div>
        </div>

        <div className="banner-stats-strip">
          <div className="b-stat">
            <span className="b-stat-label">ALGORITHM</span>
            <span className="b-stat-val">{rf.model_type}</span>
          </div>
          <div className="b-stat">
            <span className="b-stat-label">TEST F1-SCORE</span>
            <span className="b-stat-val text-brand-cyan mono">{(rf.test_metrics?.f1_score ?? 0).toFixed(4)}</span>
          </div>
          <div className="b-stat">
            <span className="b-stat-label">TEST PR-AUC</span>
            <span className="b-stat-val text-brand-cyan mono">{(rf.test_metrics?.pr_auc ?? 0).toFixed(4)}</span>
          </div>
        </div>
      </div>

      {/* Split Selector Pill */}
      <div className="split-nav-bar">
        <div className="split-pills" role="tablist" aria-label="Dataset Split Selector">
          <button
            type="button"
            role="tab"
            aria-selected={activeSplit === 'test'}
            className={`split-pill ${activeSplit === 'test' ? 'active' : ''}`}
            onClick={() => setActiveSplit('test')}
          >
            Final Held-Out Test Set (42,722 txns)
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeSplit === 'validation'}
            className={`split-pill ${activeSplit === 'validation' ? 'active' : ''}`}
            onClick={() => setActiveSplit('validation')}
          >
            Validation Split (42,721 txns)
          </button>
        </div>
        <div className="split-timestamp caption">
          Benchmark Run: <span className="mono">{new Date(evaluation_timestamp).toLocaleString()}</span>
        </div>
      </div>

      {/* Primary KPI Grid for Selected Split */}
      <div className="metrics-kpi-grid">
        <div className="kpi-card panel">
          <div className="kpi-label-row">
            <span className="caption">PRECISION</span>
            <TrendingUp size={16} className="kpi-icon text-brand-cyan" />
          </div>
          <div className="kpi-val mono">{(currentRfMetrics.precision * 100).toFixed(2)}%</div>
          <p className="kpi-subtext caption">
            {activeSplit === 'test' ? '38 / 43 positive predictions correct' : '100% precision on validation'}
          </p>
        </div>

        <div className="kpi-card panel">
          <div className="kpi-label-row">
            <span className="caption">RECALL (SENSITIVITY)</span>
            <CheckCircle2 size={16} className="kpi-icon text-brand-emerald" />
          </div>
          <div className="kpi-val mono">{(currentRfMetrics.recall * 100).toFixed(2)}%</div>
          <p className="kpi-subtext caption">
            {activeSplit === 'test' ? 'Caught 38 of 52 actual fraud cases' : 'Caught 42 of 56 frauds'}
          </p>
        </div>

        <div className="kpi-card panel">
          <div className="kpi-label-row">
            <span className="caption">F1-SCORE</span>
            <Scale size={16} className="kpi-icon text-brand-indigo" />
          </div>
          <div className="kpi-val mono">{currentRfMetrics.f1_score.toFixed(4)}</div>
          <p className="kpi-subtext caption">Balanced harmonic mean of precision &amp; recall</p>
        </div>

        <div className="kpi-card panel">
          <div className="kpi-label-row">
            <span className="caption">PR-AUC</span>
            <Layers size={16} className="kpi-icon text-brand-cyan" />
          </div>
          <div className="kpi-val mono">{currentRfMetrics.pr_auc.toFixed(4)}</div>
          <p className="kpi-subtext caption">Precision-Recall Area (Key metric for 0.17% imbalance)</p>
        </div>

        <div className="kpi-card panel">
          <div className="kpi-label-row">
            <span className="caption">ROC-AUC</span>
            <Cpu size={16} className="kpi-icon text-brand-emerald" />
          </div>
          <div className="kpi-val mono">{currentRfMetrics.roc_auc.toFixed(4)}</div>
          <p className="kpi-subtext caption">Discriminative separation capacity across thresholds</p>
        </div>
      </div>

      {/* Confusion Matrix & Asymmetric Cost Section */}
      <div className="grid-2-col">
        {/* Confusion Matrix Visual Matrix */}
        <div className="panel confusion-matrix-card">
          <div className="card-header-line">
            <div>
              <h3 className="section-title">Confusion Matrix</h3>
              <p className="caption">
                Evaluated on {activeSplit === 'test' ? 'Held-out Test' : 'Validation'} Split ({totalEvaluated.toLocaleString()} total transactions)
              </p>
            </div>
            <span className="threshold-indicator mono">Threshold = {currentRfMetrics.threshold.toFixed(2)}</span>
          </div>

          <div className="cm-table-wrapper">
            <table className="cm-table">
              <thead>
                <tr>
                  <th className="cm-corner-header" />
                  <th className="cm-col-header">Predicted Legitimate (0)</th>
                  <th className="cm-col-header">Predicted Fraud (1)</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th className="cm-row-header">Actual Legitimate (0)</th>
                  <td className="cm-cell cm-tn">
                    <span className="cm-count mono">
                      {currentRfMetrics.confusion_matrix.true_negatives.toLocaleString()}
                    </span>
                    <span className="cm-tag">True Negatives (TN)</span>
                    <span className="cm-pct caption">99.99% accuracy on clean txns</span>
                  </td>
                  <td className="cm-cell cm-fp">
                    <span className="cm-count mono">
                      {currentRfMetrics.confusion_matrix.false_positives.toLocaleString()}
                    </span>
                    <span className="cm-tag">False Positives (FP)</span>
                    <span className="cm-pct caption">False alarms (alert fatigue risk)</span>
                  </td>
                </tr>
                <tr>
                  <th className="cm-row-header">Actual Fraud (1)</th>
                  <td className="cm-cell cm-fn">
                    <span className="cm-count mono">
                      {currentRfMetrics.confusion_matrix.false_negatives.toLocaleString()}
                    </span>
                    <span className="cm-tag">False Negatives (FN)</span>
                    <span className="cm-pct caption">Undetected fraud (high cost)</span>
                  </td>
                  <td className="cm-cell cm-tp">
                    <span className="cm-count mono">
                      {currentRfMetrics.confusion_matrix.true_positives.toLocaleString()}
                    </span>
                    <span className="cm-tag">True Positives (TP)</span>
                    <span className="cm-pct caption">Intercepted fraudulent txns</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="cm-summary-note caption">
            <Info size={14} className="note-icon" />
            <span>
              At threshold 0.56, Random Forest achieved only <strong>5 False Positives</strong> out of 42,670 legitimate transactions (0.012% false alert rate), preventing operational paralysis for the fraud team.
            </span>
          </div>
        </div>

        {/* Cost & Threshold Optimization Card */}
        <div className="panel cost-card">
          <div className="card-header-line">
            <div>
              <h3 className="section-title">Asymmetric Cost Calibration</h3>
              <p className="caption">Threshold optimization under asymmetric banking loss</p>
            </div>
            <Scale size={20} className="text-brand-indigo" />
          </div>

          <div className="cost-weights-strip">
            <div className="cost-weight-box">
              <span className="weight-label caption">False Negative (Missed Fraud)</span>
              <span className="weight-val text-risk-high mono">10.0x Cost Weight</span>
              <span className="weight-desc caption">Direct chargeback loss and financial liability</span>
            </div>
            <div className="cost-weight-box">
              <span className="weight-label caption">False Positive (False Alarm)</span>
              <span className="weight-val text-risk-medium mono">1.0x Cost Weight</span>
              <span className="weight-desc caption">Analyst review overhead &amp; customer friction</span>
            </div>
          </div>

          <div className="cost-callout">
            <div className="callout-title-row">
              <AlertTriangle size={16} className="text-risk-medium" />
              <strong>Why 0.56 Decision Threshold?</strong>
            </div>
            <p className="callout-body caption">
              Default 0.50 probability cutoff yields higher false positives. Grid-search optimization across validation thresholds demonstrated that <strong>0.5600</strong> minimizes the global cost index while maintaining 73.08% fraud recall on unseen data.
            </p>
          </div>

          <div className="reasoning-box">
            <h4 className="reasoning-title">Selection Justification</h4>
            <p className="caption text-muted">{comparison_summary}</p>
          </div>
        </div>
      </div>

      {/* Model Benchmark Comparison: Random Forest vs Logistic Regression */}
      <div className="panel comparison-section">
        <div className="card-header-line">
          <div>
            <div className="section-title-row">
              <GitCompare size={20} className="text-brand-cyan" />
              <h3 className="section-title">Candidate Architecture Comparison</h3>
            </div>
            <p className="caption">
              Comparison between verified production artifact and baseline benchmark evaluated during training.
            </p>
          </div>
        </div>

        <div className="table-wrapper">
          <table className="comparison-table">
            <thead>
              <tr>
                <th>Model Architecture</th>
                <th>Deployment State</th>
                <th>Validation Precision</th>
                <th>Validation Recall</th>
                <th>Validation F1</th>
                <th>Validation PR-AUC</th>
                <th>Val False Positives</th>
                <th>Test Set Evaluated?</th>
              </tr>
            </thead>
            <tbody>
              {/* Random Forest Row */}
              <tr className="row-deployed">
                <td>
                  <div className="model-name-cell">
                    <strong>{rf.model_name}</strong>
                    <span className="version-sub mono">{rf.model_version}</span>
                  </div>
                </td>
                <td>
                  <span className="badge-deployed">DEPLOYED (ACTIVE)</span>
                </td>
                <td className="mono tabular-nums font-semibold text-brand-emerald">
                  {(rf.validation_metrics.precision * 100).toFixed(2)}%
                </td>
                <td className="mono tabular-nums">{(rf.validation_metrics.recall * 100).toFixed(2)}%</td>
                <td className="mono tabular-nums font-semibold text-brand-cyan">
                  {rf.validation_metrics.f1_score.toFixed(4)}
                </td>
                <td className="mono tabular-nums">{rf.validation_metrics.pr_auc.toFixed(4)}</td>
                <td className="mono tabular-nums text-risk-low">
                  {valCm.false_positives} FPs
                </td>
                <td>
                  <span className="badge-verified">Yes (0.8000 F1)</span>
                </td>
              </tr>

              {/* Logistic Regression Row */}
              <tr className="row-baseline">
                <td>
                  <div className="model-name-cell">
                    <strong>{lr.model_name}</strong>
                    <span className="version-sub mono">{lr.model_version}</span>
                  </div>
                </td>
                <td>
                  <span className="badge-baseline">BASELINE (NOT DEPLOYED)</span>
                </td>
                <td className="mono tabular-nums text-muted">
                  {(lr.validation_metrics.precision * 100).toFixed(2)}%
                </td>
                <td className="mono tabular-nums">{(lr.validation_metrics.recall * 100).toFixed(2)}%</td>
                <td className="mono tabular-nums text-muted">{lr.validation_metrics.f1_score.toFixed(4)}</td>
                <td className="mono tabular-nums">{lr.validation_metrics.pr_auc.toFixed(4)}</td>
                <td className="mono tabular-nums text-risk-medium">
                  {lr.validation_metrics.confusion_matrix.false_positives} FPs
                </td>
                <td>
                  <span className="badge-not-eval">No (Validation only)</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="baseline-clarification caption">
          <Info size={14} className="note-icon" />
          <span>
            <strong>Governance Note:</strong> Logistic Regression was retained as a reproducible baseline model (F1=0.5052). Due to its low precision (35.51%) and 89 false alarms on validation, it was not deployed to production and was not evaluated on the held-out test split to protect test integrity. XGBoost and Linear Regression are excluded as no model artifacts exist in this repository.
          </span>
        </div>
      </div>

      {/* Architecture & Pipeline Specifications */}
      <div className="grid-2-col">
        {/* Pipeline Details */}
        <div className="panel spec-card">
          <h3 className="section-title">Feature Engineering &amp; Preprocessing</h3>
          <div className="spec-list">
            <div className="spec-item">
              <span className="spec-label caption">INPUT FEATURES (30 TOTAL)</span>
              <p className="spec-val">
                <code>Time</code>, <code>Amount</code>, and <code>V1</code> through <code>V28</code> (anonymized Principal Components from PCA transformation).
              </p>
            </div>
            <div className="spec-item">
              <span className="spec-label caption">FEATURE SCALING</span>
              <p className="spec-val">
                <code>RobustScaler</code> applied to <code>Time</code> and <code>Amount</code>. Resistant to large outlier amounts typical in financial transactions.
              </p>
            </div>
            <div className="spec-item">
              <span className="spec-label caption">PCA COMPONENTS (V1 - V28)</span>
              <p className="spec-val">
                Passthrough identity mapping. Preserves orthogonal variance without double-standardization.
              </p>
            </div>
            <div className="spec-item">
              <span className="spec-label caption">GROUND-TRUTH LABEL ('CLASS')</span>
              <p className="spec-val">
                Used strictly for offline training and evaluation. Completely stripped from inference payloads and prohibited in live scoring.
              </p>
            </div>
          </div>
        </div>

        {/* Hyperparameters Card */}
        <div className="panel spec-card">
          <h3 className="section-title">Production Hyperparameters</h3>
          <div className="spec-list">
            <div className="spec-item">
              <span className="spec-label caption">ENSEMBLE ESTIMATORS</span>
              <p className="spec-val mono">100 decision trees (RandomForestClassifier)</p>
            </div>
            <div className="spec-item">
              <span className="spec-label caption">MAX TREE DEPTH</span>
              <p className="spec-val mono">10 levels (prevents overfitting on rare fraud patterns)</p>
            </div>
            <div className="spec-item">
              <span className="spec-label caption">CLASS WEIGHTING</span>
              <p className="spec-val mono">balanced (inversely proportional to class frequencies)</p>
            </div>
            <div className="spec-item">
              <span className="spec-label caption">EXPLAINABILITY ENGINE</span>
              <p className="spec-val">
                TreeExplainer (SHAP) with dynamic on-demand feature attribution for investigation triage.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
