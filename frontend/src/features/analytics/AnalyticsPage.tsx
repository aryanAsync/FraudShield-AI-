import React, { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  AreaChart,
  Area,
} from 'recharts'
import {
  HelpCircle,
  ChevronDown,
  ChevronUp,
  Info,
} from 'lucide-react'
import { analyticsApi } from '../../api'
import type { RiskLevel } from '../../api/types'
import { RiskBadge } from '../../components/risk/RiskBadge'
import { StatusBadge } from '../../components/risk/StatusBadge'
import { Skeleton } from '../../components/ui/Skeleton'
import { ErrorState } from '../../components/feedback/ErrorState'
import { EmptyState } from '../../components/feedback/EmptyState'
import { SHAP_DISCLAIMER } from '../../lib/constants'
import { formatSeconds } from '../../lib/format'
import { computeDateRange } from '../../lib/dates'
import './AnalyticsPage.css'

export const AnalyticsPage: React.FC = () => {
  const [interval, setInterval] = useState<'day' | 'hour'>('day')
  const [rangePreset, setRangePreset] = useState<'7d' | '30d' | '90d' | 'all'>('30d')
  const [riskFilter, setRiskFilter] = useState<RiskLevel>('HIGH')
  const [featureLimit, setFeatureLimit] = useState<number>(10)
  const [showDefinitions, setShowDefinitions] = useState<boolean>(false)

  // Compute date bounds
  const { start_date, end_date } = useMemo(() => computeDateRange(rangePreset), [rangePreset])

  // 1. Risk Distribution
  const riskQuery = useQuery({
    queryKey: ['analytics-page-risk', start_date, end_date],
    queryFn: () => analyticsApi.getRiskDistribution({ start_date, end_date }),
  })

  // 2. Trends
  const trendsQuery = useQuery({
    queryKey: ['analytics-page-trends', interval, start_date, end_date],
    queryFn: () => analyticsApi.getTrends(interval, { start_date, end_date }),
  })

  // 3. Case Status Distribution
  const caseStatusQuery = useQuery({
    queryKey: ['analytics-page-case-status', start_date, end_date],
    queryFn: () => analyticsApi.getCaseStatusDistribution({ start_date, end_date }),
  })

  // 4. Feature Importance
  const featureQuery = useQuery({
    queryKey: ['analytics-page-features', riskFilter, featureLimit, start_date, end_date],
    queryFn: () =>
      analyticsApi.getFeatureImportance({
        risk_level: riskFilter,
        limit: featureLimit,
        start_date,
        end_date,
      }),
  })

  return (
    <div className="analytics-page">
      {/* Page Header with Controls */}
      <div className="analytics-header">
        <div>
          <h1 className="page-title">Operational Analytics & Telemetry</h1>
          <p className="caption">
            Comprehensive metric breakdowns, inference time-series trends, and SHAP model explainability.
          </p>
        </div>

        {/* Global Controls */}
        <div className="analytics-controls-row">
          <div className="range-filter-group" role="group" aria-label="Aggregation interval">
            <button
              type="button"
              className={`range-pill-btn ${interval === 'day' ? 'active' : ''}`}
              onClick={() => setInterval('day')}
            >
              Daily
            </button>
            <button
              type="button"
              className={`range-pill-btn ${interval === 'hour' ? 'active' : ''}`}
              onClick={() => {
                if (rangePreset === 'all' || rangePreset === '90d') {
                  setRangePreset('7d')
                }
                setInterval('hour')
              }}
              title="Hourly aggregation (requires ≤ 30 days)"
            >
              Hourly
            </button>
          </div>

          <div className="range-filter-group" role="group" aria-label="Date range selector">
            <button
              type="button"
              className={`range-pill-btn ${rangePreset === '7d' ? 'active' : ''}`}
              onClick={() => setRangePreset('7d')}
            >
              7 Days
            </button>
            <button
              type="button"
              className={`range-pill-btn ${rangePreset === '30d' ? 'active' : ''}`}
              onClick={() => setRangePreset('30d')}
            >
              30 Days
            </button>
            {interval !== 'hour' && (
              <>
                <button
                  type="button"
                  className={`range-pill-btn ${rangePreset === '90d' ? 'active' : ''}`}
                  onClick={() => setRangePreset('90d')}
                >
                  90 Days
                </button>
                <button
                  type="button"
                  className={`range-pill-btn ${rangePreset === 'all' ? 'active' : ''}`}
                  onClick={() => setRangePreset('all')}
                >
                  All Time
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Section 1: Evaluation Trends */}
      <section className="analytics-section panel" aria-labelledby="eval-trends-title">
        <div className="section-header">
          <div>
            <h2 id="eval-trends-title" className="section-title">
              Inference & Flagged Fraud Time Series
            </h2>
            <p className="caption">
              Total transaction evaluations plotted alongside predictions flagged as fraud ({interval} interval)
            </p>
          </div>
        </div>

        <div className="section-body">
          {trendsQuery.isLoading ? (
            <Skeleton height="280px" />
          ) : trendsQuery.isError ? (
            <ErrorState error={trendsQuery.error} onRetry={() => trendsQuery.refetch()} />
          ) : !trendsQuery.data?.items?.length ? (
            <EmptyState title="No trend evaluations" description="No evaluation events recorded in this window." />
          ) : (
            <div className="chart-container">
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart
                  data={trendsQuery.data.items.map((i) => ({
                    time:
                      interval === 'hour'
                        ? i.timestamp.replace('T', ' ').substring(5, 16)
                        : i.timestamp.split('T')[0],
                    evaluations: i.prediction_count,
                    fraud: i.predicted_fraud_count,
                    highRisk: i.high_risk_count,
                  }))}
                  margin={{ top: 10, right: 20, left: -20, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-default)" vertical={false} />
                  <XAxis dataKey="time" stroke="var(--text-tertiary)" fontSize={11} tickLine={false} />
                  <YAxis stroke="var(--text-tertiary)" fontSize={11} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'var(--bg-surface)',
                      borderColor: 'var(--border-default)',
                      borderRadius: 'var(--radius-md)',
                      fontSize: '12px',
                      boxShadow: 'var(--shadow-dropdown)',
                    }}
                  />
                  <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '12px' }} />
                  <Area
                    type="monotone"
                    dataKey="evaluations"
                    stroke="var(--accent-600)"
                    fill="var(--accent-100)"
                    strokeWidth={2}
                    name="Evaluations"
                  />
                  <Area
                    type="monotone"
                    dataKey="highRisk"
                    stroke="var(--risk-med-text)"
                    fill="var(--risk-med-bg)"
                    strokeWidth={1.5}
                    name="High Risk Tier"
                  />
                  <Area
                    type="monotone"
                    dataKey="fraud"
                    stroke="var(--risk-high-text)"
                    fill="var(--risk-high-bg)"
                    strokeWidth={2}
                    name="Flagged Fraud"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </section>

      {/* Section 2: Two Columns: Risk Distribution & Case Distribution */}
      <div className="analytics-grid-2col">
        {/* Risk Distribution Breakdown */}
        <section className="analytics-section panel" aria-labelledby="risk-breakdown-title">
          <div className="section-header">
            <div>
              <h2 id="risk-breakdown-title" className="section-title">
                Risk Tier Distribution
              </h2>
              <p className="caption">Breakdown evaluated strictly on latest prediction per transaction</p>
            </div>
          </div>

          <div className="section-body">
            {riskQuery.isLoading ? (
              <Skeleton height="240px" />
            ) : riskQuery.isError ? (
              <ErrorState error={riskQuery.error} onRetry={() => riskQuery.refetch()} />
            ) : !riskQuery.data?.items?.length ? (
              <EmptyState title="No risk records" description="No evaluated records available." />
            ) : (
              <div className="risk-analytics-container">
                <table className="mini-data-table">
                  <thead>
                    <tr>
                      <th>Tier</th>
                      <th className="align-right">Evaluations</th>
                      <th className="align-right">Percentage</th>
                    </tr>
                  </thead>
                  <tbody>
                    {riskQuery.data.items.map((item) => (
                      <tr key={item.risk_level}>
                        <td>
                          <RiskBadge level={item.risk_level} size="sm" />
                        </td>
                        <td className="align-right mono">{item.count.toLocaleString()}</td>
                        <td className="align-right mono font-semibold">{item.percentage.toFixed(2)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                <div className="classification-box panel-subtle">
                  <div className="classification-stat">
                    <span className="caption">Evaluated Transactions:</span>
                    <strong className="mono">{riskQuery.data.total_transactions.toLocaleString()}</strong>
                  </div>
                  <div className="classification-stat">
                    <span className="caption">Predicted Fraud (Class 1):</span>
                    <strong className="mono text-danger">
                      {riskQuery.data.classification.predicted_fraud_count.toLocaleString()} (
                      {riskQuery.data.classification.predicted_fraud_percentage.toFixed(2)}%)
                    </strong>
                  </div>
                  <div className="classification-stat">
                    <span className="caption">Predicted Legitimate (Class 0):</span>
                    <strong className="mono text-success">
                      {riskQuery.data.classification.predicted_legitimate_count.toLocaleString()} (
                      {riskQuery.data.classification.predicted_legitimate_percentage.toFixed(2)}%)
                    </strong>
                  </div>
                </div>
              </div>
            )}
          </div>
        </section>

        {/* Case Status Pipeline Breakdown */}
        <section className="analytics-section panel" aria-labelledby="case-breakdown-title">
          <div className="section-header">
            <div>
              <h2 id="case-breakdown-title" className="section-title">
                Investigation Workflow Statuses
              </h2>
              <p className="caption">Operational workload, resolutions, and average resolution time</p>
            </div>
          </div>

          <div className="section-body">
            {caseStatusQuery.isLoading ? (
              <Skeleton height="240px" />
            ) : caseStatusQuery.isError ? (
              <ErrorState error={caseStatusQuery.error} onRetry={() => caseStatusQuery.refetch()} />
            ) : !caseStatusQuery.data?.items?.length ? (
              <EmptyState title="No investigation cases" description="No cases recorded." />
            ) : (
              <div className="case-analytics-container">
                <table className="mini-data-table">
                  <thead>
                    <tr>
                      <th>Status</th>
                      <th className="align-right">Cases</th>
                      <th className="align-right">Share</th>
                    </tr>
                  </thead>
                  <tbody>
                    {caseStatusQuery.data.items.map((item) => (
                      <tr key={item.status}>
                        <td>
                          <StatusBadge status={item.status} size="sm" />
                        </td>
                        <td className="align-right mono">{item.count.toLocaleString()}</td>
                        <td className="align-right mono font-semibold">{item.percentage.toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                <div className="classification-box panel-subtle">
                  <div className="classification-stat">
                    <span className="caption">Active Unresolved Cases:</span>
                    <strong className="mono text-accent">
                      {caseStatusQuery.data.summary.unresolved_count}
                    </strong>
                  </div>
                  <div className="classification-stat">
                    <span className="caption">Human Confirmed Fraud:</span>
                    <strong className="mono text-danger">
                      {caseStatusQuery.data.summary.resolved_fraud_count}
                    </strong>
                  </div>
                  <div className="classification-stat">
                    <span className="caption">Avg Resolution Duration:</span>
                    <strong className="mono">
                      {formatSeconds(caseStatusQuery.data.summary.average_resolution_time_seconds)}
                    </strong>
                  </div>
                </div>

                <div className="footnote caption">
                  Reflects current stored status. Closed cases are archived in terminal state.
                </div>
              </div>
            )}
          </div>
        </section>
      </div>

      {/* Section 3: Feature Importance (Aggregated SHAP) */}
      <section className="analytics-section panel" aria-labelledby="shap-features-title">
        <div className="section-header">
          <div>
            <h2 id="shap-features-title" className="section-title">
              Aggregated Model Feature Attribution (SHAP)
            </h2>
            <p className="caption">
              Mean absolute contribution of features across evaluated transactions, ranked by risk impact
            </p>
          </div>

          <div className="feature-controls">
            <div className="control-item">
              <label htmlFor="tier-select" className="caption">
                Target Risk Tier:
              </label>
              <select
                id="tier-select"
                className="select-mini mono"
                value={riskFilter}
                onChange={(e) => setRiskFilter(e.target.value as RiskLevel)}
              >
                <option value="HIGH">HIGH Risk</option>
                <option value="MEDIUM">MEDIUM Risk</option>
                <option value="LOW">LOW Risk</option>
              </select>
            </div>

            <div className="control-item">
              <label htmlFor="limit-select" className="caption">
                Features:
              </label>
              <select
                id="limit-select"
                className="select-mini mono"
                value={featureLimit}
                onChange={(e) => setFeatureLimit(Number(e.target.value))}
              >
                <option value={10}>Top 10</option>
                <option value={20}>Top 20</option>
                <option value={30}>All 30</option>
              </select>
            </div>
          </div>
        </div>

        <div className="section-body">
          {featureQuery.isLoading ? (
            <Skeleton height="260px" />
          ) : featureQuery.isError ? (
            <ErrorState error={featureQuery.error} onRetry={() => featureQuery.refetch()} />
          ) : !featureQuery.data?.features?.length ? (
            <EmptyState
              title="No SHAP explanations"
              description="No stored prediction explanations match this risk tier."
            />
          ) : (
            <div className="feature-imp-full-container">
              <div className="feature-chart-wrapper">
                <ResponsiveContainer width="100%" height={Math.max(featureQuery.data.features.length * 28, 240)}>
                  <BarChart
                    data={featureQuery.data.features.map((f) => ({
                      feature: f.feature,
                      importance: f.mean_absolute_attribution,
                      samples: f.sample_count,
                    }))}
                    layout="vertical"
                    margin={{ top: 5, right: 30, left: 30, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-default)" horizontal={false} />
                    <XAxis type="number" stroke="var(--text-tertiary)" fontSize={11} tickLine={false} />
                    <YAxis dataKey="feature" type="category" stroke="var(--text-primary)" fontSize={12} tickLine={false} width={60} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'var(--bg-surface)',
                        borderColor: 'var(--border-default)',
                        borderRadius: 'var(--radius-md)',
                        fontSize: '12px',
                        boxShadow: 'var(--shadow-dropdown)',
                      }}
                      formatter={(val: any) => [Number(val).toFixed(4), 'Mean |SHAP|']}
                    />
                    <Bar dataKey="importance" fill="var(--accent-600)" radius={[0, 4, 4, 0]} name="Mean |SHAP|" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="feature-disclaimer caption">
                <Info size={14} className="disclaimer-icon" />
                <span>{featureQuery.data.disclaimer || SHAP_DISCLAIMER}</span>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Section 4: Collapsible Metric Definitions Panel */}
      <section className="analytics-section panel" aria-label="Metric Definitions">
        <button
          type="button"
          className="definitions-toggle-btn"
          onClick={() => setShowDefinitions(!showDefinitions)}
          aria-expanded={showDefinitions}
        >
          <div className="definitions-toggle-title">
            <HelpCircle size={16} />
            <span>Metric Definitions & Backend Semantics Reference</span>
          </div>
          {showDefinitions ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>

        {showDefinitions && (
          <div className="definitions-content">
            <div className="definition-row">
              <div className="definition-term mono">Evaluated Transactions</div>
              <div className="definition-desc caption">
                Distinct transactions stored in PostgreSQL evaluated by at least one model inference snapshot. Uses latest prediction per transaction to avoid duplicate counts.
              </div>
            </div>
            <div className="definition-row">
              <div className="definition-term mono">Predicted Fraud vs Confirmed Fraud</div>
              <div className="definition-desc caption">
                <strong>Predicted Fraud</strong> represents model machine inference flagging <code>predicted_class = 1</code> based on decision threshold. <strong>Confirmed Fraud</strong> represents final human adjudication recorded on a case by an analyst or administrator.
              </div>
            </div>
            <div className="definition-row">
              <div className="definition-term mono">SHAP Attributions</div>
              <div className="definition-desc caption">
                Shapley Additive Explanations quantifying feature contributions pushing toward or away from the model's fraud decision boundary. V1 through V28 are anonymized PCA dimensions and carry no interpretable physical or demographic meaning.
              </div>
            </div>
            <div className="definition-row">
              <div className="definition-term mono">Trend Aggregation</div>
              <div className="definition-desc caption">
                Time-series counts aggregated by inference execution timestamp (<code>predicted_at</code> UTC). Hourly aggregations are restricted by the server to a maximum 30-day window.
              </div>
            </div>
          </div>
        )}
      </section>
    </div>
  )
}
