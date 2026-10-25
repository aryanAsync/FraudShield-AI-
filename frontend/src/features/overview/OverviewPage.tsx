import React, { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts'
import {
  Info,
  ArrowUpRight,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { analyticsApi } from '../../api'
import { RiskBadge } from '../../components/risk/RiskBadge'
import { StatusBadge } from '../../components/risk/StatusBadge'
import { Skeleton } from '../../components/ui/Skeleton'
import { ErrorState } from '../../components/feedback/ErrorState'
import { EmptyState } from '../../components/feedback/EmptyState'
import { SHAP_DISCLAIMER } from '../../lib/constants'
import { computeDateRange } from '../../lib/dates'
import './OverviewPage.css'

export const OverviewPage: React.FC = () => {
  // Date range state: 7d, 30d, all
  const [rangePreset, setRangePreset] = useState<'7d' | '30d' | 'all'>('7d')
  const [viewTableTwins, setViewTableTwins] = useState<Record<string, boolean>>({})

  const toggleTableTwin = (widgetId: string) => {
    setViewTableTwins((prev) => ({ ...prev, [widgetId]: !prev[widgetId] }))
  }

  // Derive start/end ISO strings based on preset
  const { start_date, end_date } = useMemo(() => computeDateRange(rangePreset), [rangePreset])

  // 1. Overview KPIs
  const overviewQuery = useQuery({
    queryKey: ['analytics-overview', start_date, end_date],
    queryFn: () => analyticsApi.getOverview({ start_date, end_date }),
  })

  // 2. Risk Distribution
  const riskQuery = useQuery({
    queryKey: ['analytics-risk-distribution', start_date, end_date],
    queryFn: () => analyticsApi.getRiskDistribution({ start_date, end_date }),
  })

  // 3. Trends (daily)
  const trendsQuery = useQuery({
    queryKey: ['analytics-trends', 'day', start_date, end_date],
    queryFn: () => analyticsApi.getTrends('day', { start_date, end_date }),
  })

  // 4. Case Status Distribution
  const caseStatusQuery = useQuery({
    queryKey: ['analytics-case-status', start_date, end_date],
    queryFn: () => analyticsApi.getCaseStatusDistribution({ start_date, end_date }),
  })

  // 5. Feature Importance Top 5 Preview
  const featureQuery = useQuery({
    queryKey: ['analytics-feature-importance', 'HIGH', 5, start_date, end_date],
    queryFn: () =>
      analyticsApi.getFeatureImportance({
        risk_level: 'HIGH',
        limit: 5,
        start_date,
        end_date,
      }),
  })

  const overview = overviewQuery.data

  return (
    <div className="overview-page">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Executive Risk Overview</h1>
          <p className="caption">
            Real-time telemetry on evaluated financial transactions, ML risk categorization, and
            investigation pipeline.
          </p>
        </div>

        {/* Date Filter Bar */}
        <div className="range-filter-group" role="group" aria-label="Date range selector">
          <button
            type="button"
            className={`range-pill-btn ${rangePreset === '7d' ? 'active' : ''}`}
            onClick={() => setRangePreset('7d')}
          >
            Last 7 Days
          </button>
          <button
            type="button"
            className={`range-pill-btn ${rangePreset === '30d' ? 'active' : ''}`}
            onClick={() => setRangePreset('30d')}
          >
            Last 30 Days
          </button>
          <button
            type="button"
            className={`range-pill-btn ${rangePreset === 'all' ? 'active' : ''}`}
            onClick={() => setRangePreset('all')}
          >
            All Time
          </button>
        </div>
      </div>

      {/* Tier 1: Primary Summary Strip (Single wide panel) */}
      <section className="summary-strip-panel panel" aria-label="Primary Risk Indicators">
        {overviewQuery.isLoading ? (
          <div className="summary-strip-skeleton">
            <Skeleton height="72px" />
          </div>
        ) : overviewQuery.isError ? (
          <ErrorState
            title="Failed to load summary KPIs"
            error={overviewQuery.error}
            onRetry={() => overviewQuery.refetch()}
          />
        ) : overview ? (
          <div className="summary-strip-content">
            {/* Primary KPI: Evaluated Transactions */}
            <div className="primary-metric-block">
              <span className="metric-label caption">EVALUATED TRANSACTIONS</span>
              <div className="metric-val mono">{overview.transactions.total_transactions.toLocaleString()}</div>
              <span className="metric-sub caption">
                {overview.transactions.transactions_with_predictions.toLocaleString()} with ML predictions
              </span>
            </div>

            {/* Hairline Divider */}
            <div className="metric-divider" />

            {/* Secondary 1: Predicted Fraud */}
            <div className="secondary-metric-block">
              <span className="metric-label caption">PREDICTED FRAUD</span>
              <div className="metric-val mono text-danger">
                {overview.transactions.predicted_fraud_count.toLocaleString()}
              </div>
              <span className="metric-sub caption">
                {overview.transactions.predicted_fraud_percentage.toFixed(2)}% of evaluated
              </span>
            </div>

            {/* Hairline Divider */}
            <div className="metric-divider" />

            {/* Secondary 2: High Risk Tier */}
            <div className="secondary-metric-block">
              <span className="metric-label caption">HIGH RISK TIER</span>
              <div className="metric-val mono text-high-risk">
                {overview.risk.high_risk_transactions.toLocaleString()}
              </div>
              <span className="metric-sub caption">
                Avg score: {overview.risk.average_risk_score.toFixed(1)} / 100
              </span>
            </div>

            {/* Hairline Divider */}
            <div className="metric-divider" />

            {/* Secondary 3: Active Investigations */}
            <div className="secondary-metric-block">
              <span className="metric-label caption">OPEN INVESTIGATIONS</span>
              <div className="metric-val mono text-accent">
                {overview.cases.unresolved.toLocaleString()}
              </div>
              <span className="metric-sub caption">
                {overview.cases.open} open &bull; {overview.cases.in_review} in review
              </span>
            </div>
          </div>
        ) : null}
      </section>

      {/* Tier 2 & 3: Trend Time-Series and Risk Distribution */}
      <div className="dashboard-grid-2col">
        {/* Widget 1: Trends Chart */}
        <section className="widget-card panel" aria-labelledby="trends-heading">
          <div className="widget-header">
            <div>
              <h2 id="trends-heading" className="widget-title">
                Evaluation & Prediction Trends
              </h2>
              <p className="caption">Daily volume of evaluated events vs flagged fraud predictions</p>
            </div>
            <button
              type="button"
              className="table-twin-toggle-btn caption"
              onClick={() => toggleTableTwin('trends')}
            >
              {viewTableTwins['trends'] ? 'View Chart' : 'View as Table'}
            </button>
          </div>

          <div className="widget-body">
            {trendsQuery.isLoading ? (
              <Skeleton height="240px" />
            ) : trendsQuery.isError ? (
              <ErrorState error={trendsQuery.error} onRetry={() => trendsQuery.refetch()} />
            ) : !trendsQuery.data?.items?.length ? (
              <EmptyState title="No trend data" description="No evaluation events found in this date window." />
            ) : viewTableTwins['trends'] ? (
              <div className="table-twin-scroll">
                <table className="mini-data-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th className="align-right">Evaluations</th>
                      <th className="align-right">Flagged Fraud</th>
                      <th className="align-right">Avg Risk</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trendsQuery.data.items.map((item, idx) => (
                      <tr key={idx}>
                        <td className="mono">{item.timestamp.split('T')[0]}</td>
                        <td className="align-right mono">{item.prediction_count}</td>
                        <td className="align-right mono text-danger">{item.predicted_fraud_count}</td>
                        <td className="align-right mono">{item.average_risk_score.toFixed(1)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="chart-wrapper">
                <ResponsiveContainer width="100%" height={240}>
                  <AreaChart
                    data={trendsQuery.data.items.map((i) => ({
                      date: i.timestamp.split('T')[0],
                      evaluations: i.prediction_count,
                      fraud: i.predicted_fraud_count,
                    }))}
                    margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-default)" vertical={false} />
                    <XAxis dataKey="date" stroke="var(--text-tertiary)" fontSize={11} tickLine={false} />
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
                    <Area
                      type="monotone"
                      dataKey="evaluations"
                      stroke="var(--accent-600)"
                      fill="var(--accent-100)"
                      strokeWidth={2}
                      name="Total Evaluations"
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

        {/* Widget 2: Risk Distribution */}
        <section className="widget-card panel" aria-labelledby="risk-dist-heading">
          <div className="widget-header">
            <div>
              <h2 id="risk-dist-heading" className="widget-title">
                Risk Categorization
              </h2>
              <p className="caption">Categorical breakdown of latest transaction evaluations</p>
            </div>
            <button
              type="button"
              className="table-twin-toggle-btn caption"
              onClick={() => toggleTableTwin('risk')}
            >
              {viewTableTwins['risk'] ? 'View Chart' : 'View as Table'}
            </button>
          </div>

          <div className="widget-body">
            {riskQuery.isLoading ? (
              <Skeleton height="240px" />
            ) : riskQuery.isError ? (
              <ErrorState error={riskQuery.error} onRetry={() => riskQuery.refetch()} />
            ) : !riskQuery.data?.items?.length ? (
              <EmptyState title="No risk evaluations" description="No evaluated records available." />
            ) : viewTableTwins['risk'] ? (
              <table className="mini-data-table">
                <thead>
                  <tr>
                    <th>Risk Tier</th>
                    <th className="align-right">Count</th>
                    <th className="align-right">Proportion</th>
                  </tr>
                </thead>
                <tbody>
                  {riskQuery.data.items.map((item) => (
                    <tr key={item.risk_level}>
                      <td>
                        <RiskBadge level={item.risk_level} size="sm" />
                      </td>
                      <td className="align-right mono">{item.count.toLocaleString()}</td>
                      <td className="align-right mono">{item.percentage.toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="risk-bars-container">
                {riskQuery.data.items.map((item) => {
                  let barColor = 'var(--risk-low-text)'
                  if (item.risk_level === 'MEDIUM') barColor = 'var(--risk-med-text)'
                  if (item.risk_level === 'HIGH') barColor = 'var(--risk-high-text)'

                  return (
                    <div key={item.risk_level} className="risk-bar-row">
                      <div className="risk-bar-header">
                        <RiskBadge level={item.risk_level} size="sm" />
                        <span className="mono caption">
                          <strong>{item.count.toLocaleString()}</strong> ({item.percentage.toFixed(1)}%)
                        </span>
                      </div>
                      <div className="risk-bar-track">
                        <div
                          className="risk-bar-fill"
                          style={{
                            width: `${Math.max(item.percentage, 1)}%`,
                            backgroundColor: barColor,
                          }}
                        />
                      </div>
                    </div>
                  )
                })}

                {/* Binary Classification Notice */}
                <div className="classification-box panel-subtle">
                  <div className="classification-stat">
                    <span className="caption">Model Predicted Fraud:</span>
                    <strong className="mono text-danger">
                      {riskQuery.data.classification.predicted_fraud_count.toLocaleString()} (
                      {riskQuery.data.classification.predicted_fraud_percentage.toFixed(2)}%)
                    </strong>
                  </div>
                  <div className="classification-stat">
                    <span className="caption">Model Predicted Legitimate:</span>
                    <strong className="mono">
                      {riskQuery.data.classification.predicted_legitimate_count.toLocaleString()} (
                      {riskQuery.data.classification.predicted_legitimate_percentage.toFixed(2)}%)
                    </strong>
                  </div>
                </div>
              </div>
            )}
          </div>
        </section>
      </div>

      {/* Tier 4 & 5: Case Status Pipeline & Feature Importance Drivers */}
      <div className="dashboard-grid-2col">
        {/* Case Status Distribution */}
        <section className="widget-card panel" aria-labelledby="case-status-heading">
          <div className="widget-header">
            <div>
              <h2 id="case-status-heading" className="widget-title">
                Investigation Pipeline
              </h2>
              <p className="caption">Workload breakdown across current investigation statuses</p>
            </div>
            <Link to="/investigations" className="widget-action-link caption">
              <span>View Queue</span>
              <ArrowUpRight size={14} />
            </Link>
          </div>

          <div className="widget-body">
            {caseStatusQuery.isLoading ? (
              <Skeleton height="200px" />
            ) : caseStatusQuery.isError ? (
              <ErrorState error={caseStatusQuery.error} onRetry={() => caseStatusQuery.refetch()} />
            ) : !caseStatusQuery.data?.items?.length ? (
              <EmptyState title="No cases recorded" description="The investigation queue is currently empty." />
            ) : (
              <div className="case-status-container">
                <div className="case-status-grid">
                  {caseStatusQuery.data.items.map((c) => (
                    <div key={c.status} className="case-status-card panel-subtle">
                      <div className="case-status-card-header">
                        <StatusBadge status={c.status} size="sm" />
                        <span className="caption mono">{c.percentage.toFixed(1)}%</span>
                      </div>
                      <div className="case-status-card-count mono">{c.count}</div>
                    </div>
                  ))}
                </div>

                <div className="workload-summary caption">
                  <span>Assigned: <strong>{caseStatusQuery.data.summary.assigned_count}</strong></span>
                  <span>&bull;</span>
                  <span>Unassigned: <strong>{caseStatusQuery.data.summary.unassigned_count}</strong></span>
                  <span>&bull;</span>
                  <span>Pending review: <strong>{caseStatusQuery.data.summary.unresolved_count}</strong></span>
                </div>
              </div>
            )}
          </div>
        </section>

        {/* Feature Importance Preview */}
        <section className="widget-card panel" aria-labelledby="feature-imp-heading">
          <div className="widget-header">
            <div>
              <h2 id="feature-imp-heading" className="widget-title">
                Primary High-Risk Drivers (SHAP)
              </h2>
              <p className="caption">Top model input contributions across flagged high-risk transactions</p>
            </div>
            <Link to="/analytics" className="widget-action-link caption">
              <span>Full Analytics</span>
              <ArrowUpRight size={14} />
            </Link>
          </div>

          <div className="widget-body">
            {featureQuery.isLoading ? (
              <Skeleton height="200px" />
            ) : featureQuery.isError ? (
              <ErrorState error={featureQuery.error} onRetry={() => featureQuery.refetch()} />
            ) : !featureQuery.data?.features?.length ? (
              <EmptyState title="No feature explanations" description="No SHAP evaluations available in scope." />
            ) : (
              <div className="feature-imp-preview">
                {featureQuery.data.features.map((f) => (
                  <div key={f.feature} className="feature-imp-row">
                    <span className="mono feature-name-label">#{f.rank} {f.feature}</span>
                    <div className="feature-imp-bar-track">
                      <div
                        className="feature-imp-bar-fill"
                        style={{
                          width: `${Math.min(
                            (f.mean_absolute_attribution /
                              (featureQuery.data?.features[0]?.mean_absolute_attribution || 1)) *
                              100,
                            100
                          )}%`,
                        }}
                      />
                    </div>
                    <span className="mono caption feature-imp-val">
                      {f.mean_absolute_attribution.toFixed(3)}
                    </span>
                  </div>
                ))}

                <div className="feature-disclaimer caption">
                  <Info size={13} className="disclaimer-icon" />
                  <span>{featureQuery.data.disclaimer || SHAP_DISCLAIMER}</span>
                </div>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}
