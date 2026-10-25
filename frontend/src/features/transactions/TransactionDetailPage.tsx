import React, { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  Copy,
  Check,
  ShieldAlert,
  Info,
  Sparkles,
} from 'lucide-react'
import { transactionsApi, casesApi } from '../../api'
import { RiskBadge } from '../../components/risk/RiskBadge'
import { ProbabilityMeter } from '../../components/risk/ProbabilityMeter'
import { ShapBarList } from '../../components/risk/ShapBarList'
import { Button } from '../../components/ui/Button'
import { Dialog } from '../../components/ui/Dialog'
import { Input } from '../../components/ui/Input'
import { Skeleton } from '../../components/ui/Skeleton'
import { ErrorState } from '../../components/feedback/ErrorState'
import { useToast } from '../../components/ui/Toast'
import { useAuth } from '../../auth/AuthContext'
import { formatAmount, formatTimestamp } from '../../lib/format'
import { PCA_FEATURES, MODEL_ESTIMATE_NOTICE } from '../../lib/constants'
import './Transactions.css'

export const TransactionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const txId = parseInt(id || '0', 10)
  const navigate = useNavigate()
  const { role } = useAuth()
  const toast = useToast()
  const queryClient = useQueryClient()

  const [copiedFeatures, setCopiedFeatures] = useState(false)
  const [isCaseModalOpen, setIsCaseModalOpen] = useState(false)
  const [caseDescription, setCaseDescription] = useState('')

  // 1. Transaction details
  const txQuery = useQuery({
    queryKey: ['transaction-detail', txId],
    queryFn: () => transactionsApi.getById(txId),
    enabled: txId > 0,
  })

  // 2. Prediction history
  const historyQuery = useQuery({
    queryKey: ['transaction-predictions', txId],
    queryFn: () => transactionsApi.getPredictions(txId),
    enabled: txId > 0,
  })

  // Case creation mutation
  const createCaseMutation = useMutation({
    mutationFn: (desc?: string) =>
      casesApi.create({
        transaction_id: txId,
        description: desc || undefined,
      }),
    onSuccess: (newCase) => {
      toast.success(`Investigation Case #${newCase.id} created successfully.`)
      setIsCaseModalOpen(false)
      queryClient.invalidateQueries({ queryKey: ['cases-list'] })
      navigate(`/investigations/${newCase.id}`)
    },
    onError: (err: any) => {
      toast.error(err?.message || 'Failed to create investigation case.')
    },
  })

  // On-demand SHAP explainability mutation
  const explainMutation = useMutation({
    mutationFn: (k?: number) => transactionsApi.explain(txId, k || 10),
    onSuccess: () => {
      toast.success('SHAP feature attributions generated and saved.')
      queryClient.invalidateQueries({ queryKey: ['transaction-detail', txId] })
      queryClient.invalidateQueries({ queryKey: ['transaction-predictions', txId] })
    },
    onError: (err: any) => {
      toast.error(err?.message || 'Failed to compute SHAP explanation.')
    },
  })

  const handleCopyFeatures = () => {
    if (!txQuery.data) return
    const payload = {
      Time: txQuery.data.transaction_time,
      Amount: txQuery.data.amount,
      ...txQuery.data.features,
    }
    navigator.clipboard.writeText(JSON.stringify(payload, null, 2))
    setCopiedFeatures(true)
    toast.info('Feature vector copied to clipboard.')
    setTimeout(() => setCopiedFeatures(false), 2000)
  }

  const tx = txQuery.data
  const latestPred = tx?.latest_prediction

  if (txQuery.isLoading) {
    return (
      <div className="transaction-detail-page">
        <Skeleton height="36px" width="300px" />
        <div style={{ marginTop: '20px' }}>
          <Skeleton height="120px" />
        </div>
        <div style={{ marginTop: '20px' }}>
          <Skeleton height="300px" />
        </div>
      </div>
    )
  }

  if (txQuery.isError || !tx) {
    return (
      <div className="transaction-detail-page">
        <Link to="/transactions" className="back-link">
          <ArrowLeft size={16} />
          <span>Back to Transactions</span>
        </Link>
        <ErrorState
          title={`Transaction #${txId} Not Found`}
          error={txQuery.error || 'The requested transaction record does not exist.'}
          onRetry={() => txQuery.refetch()}
        />
      </div>
    )
  }

  return (
    <div className="transaction-detail-page">
      {/* Back navigation */}
      <Link to="/transactions" className="back-link">
        <ArrowLeft size={16} />
        <span>Back to Transactions</span>
      </Link>

      {/* Detail Header */}
      <div className="detail-header-panel panel">
        <div className="detail-header-main">
          <div className="detail-title-group">
            <div className="detail-id-row">
              <h1 className="detail-id-title mono">Transaction #{tx.id}</h1>
              {latestPred && <RiskBadge level={latestPred.risk_level} size="md" />}
            </div>
            <div className="detail-meta-row caption">
              <span>Submitted by: <strong>{tx.submitted_by || 'System'}</strong></span>
              <span>&bull;</span>
              <span>Recorded: {formatTimestamp(tx.created_at).display}</span>
              {tx.external_reference && (
                <>
                  <span>&bull;</span>
                  <span>Ref: <code className="mono">{tx.external_reference}</code></span>
                </>
              )}
            </div>
          </div>

          <div className="detail-header-actions">
            {(role === 'ANALYST' || role === 'ADMIN') && (
              <Button
                variant="primary"
                size="md"
                leftIcon={<ShieldAlert size={16} />}
                onClick={() => setIsCaseModalOpen(true)}
              >
                Open Investigation
              </Button>
            )}
          </div>
        </div>

        {/* Primary stats row */}
        <div className="detail-stats-strip">
          <div className="stat-card">
            <span className="caption">AMOUNT</span>
            <div className="stat-value mono tabular-nums">{formatAmount(tx.amount)}</div>
          </div>
          <div className="stat-card">
            <span className="caption">DATASET TIME</span>
            <div className="stat-value mono">{tx.transaction_time}s</div>
          </div>
          <div className="stat-card">
            <span className="caption">FRAUD PROBABILITY</span>
            <div className="stat-value mono">
              {latestPred ? (
                <ProbabilityMeter
                  probability={latestPred.fraud_probability}
                  threshold={latestPred.decision_threshold}
                  size="md"
                />
              ) : (
                '—'
              )}
            </div>
          </div>
          <div className="stat-card">
            <span className="caption">MODEL RISK SCORE</span>
            <div className="stat-value mono">
              {latestPred ? `${latestPred.risk_score.toFixed(1)} / 100` : '—'}
            </div>
          </div>
        </div>

        <div className="model-notice-banner caption">
          <Info size={14} className="notice-icon" />
          <span>{MODEL_ESTIMATE_NOTICE}</span>
        </div>
      </div>

      {/* SHAP Attributions */}
      {latestPred?.explanation && latestPred.explanation.length > 0 ? (
        <section className="detail-section" aria-labelledby="shap-section-title">
          <div className="section-header" style={{ marginBottom: '12px' }}>
            <h2 id="shap-section-title" className="section-title">
              Model Explainability (SHAP Feature Attributions)
            </h2>
            <Button
              variant="secondary"
              size="sm"
              leftIcon={<Sparkles size={14} />}
              onClick={() => explainMutation.mutate(10)}
              disabled={explainMutation.isPending}
            >
              {explainMutation.isPending ? 'Computing SHAP...' : 'Recompute SHAP'}
            </Button>
          </div>
          <ShapBarList explanations={latestPred.explanation as any} />
        </section>
      ) : (
        <section className="detail-section panel" aria-labelledby="shap-section-title">
          <div className="section-header">
            <div>
              <h2 id="shap-section-title" className="section-title">
                Model Explainability (SHAP Attributions)
              </h2>
              <p className="caption">
                Individual feature drivers pushing the model probability toward (+) or away (-) from fraud.
              </p>
            </div>
            <Button
              variant="primary"
              size="sm"
              leftIcon={<Sparkles size={14} />}
              onClick={() => explainMutation.mutate(10)}
              disabled={explainMutation.isPending}
            >
              {explainMutation.isPending ? 'Computing Attributions...' : 'Generate SHAP Explanation'}
            </Button>
          </div>
          <div className="empty-shap-box caption">
            <Info size={16} className="text-brand-cyan" />
            <span>
              SHAP feature attributions have not been pre-computed for this transaction. Click <strong>Generate SHAP Explanation</strong> to run TreeExplainer on this transaction's 30-feature vector. Features V1–V28 represent anonymized components from Principal Component Analysis (PCA).
            </span>
          </div>
        </section>
      )}

      {/* Feature Vector Section */}
      <section className="detail-section panel" aria-labelledby="features-section-title">
        <div className="section-header">
          <div>
            <h2 id="features-section-title" className="section-title">
              Complete Feature Vector ({Object.keys(tx.features || {}).length + 2} Features)
            </h2>
            <p className="caption">
              Anonymized PCA features V1–V28, Time, and Amount recorded in PostgreSQL.
            </p>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleCopyFeatures}
            leftIcon={copiedFeatures ? <Check size={14} /> : <Copy size={14} />}
          >
            {copiedFeatures ? 'Copied' : 'Copy JSON'}
          </Button>
        </div>

        <div className="feature-grid-monospaced">
          <div className="feature-cell panel-subtle">
            <span className="feature-cell-key mono">Time</span>
            <span className="feature-cell-val mono">{tx.transaction_time}</span>
          </div>
          <div className="feature-cell panel-subtle">
            <span className="feature-cell-key mono">Amount</span>
            <span className="feature-cell-val mono">{tx.amount.toFixed(2)}</span>
          </div>
          {PCA_FEATURES.map((key) => {
            const val = tx.features?.[key]
            return (
              <div key={key} className="feature-cell panel-subtle">
                <span className="feature-cell-key mono">{key}</span>
                <span className="feature-cell-val mono">
                  {val !== undefined ? val.toFixed(4) : '—'}
                </span>
              </div>
            )
          })}
        </div>
      </section>

      {/* Prediction History Section (if multiple evaluations exist) */}
      {historyQuery.data && historyQuery.data.predictions.length > 0 && (
        <section className="detail-section panel" aria-labelledby="history-section-title">
          <div className="section-header">
            <div>
              <h2 id="history-section-title" className="section-title">
                Evaluation History ({historyQuery.data.total_evaluations} Evaluations)
              </h2>
              <p className="caption">Chronological log of inference snapshots for this transaction.</p>
            </div>
          </div>

          <table className="mini-data-table">
            <thead>
              <tr>
                <th>Evaluation Timestamp</th>
                <th>Model Version</th>
                <th>Probability</th>
                <th>Risk Tier</th>
                <th>Threshold</th>
                <th>Decision</th>
              </tr>
            </thead>
            <tbody>
              {historyQuery.data.predictions.map((p) => (
                <tr key={p.id}>
                  <td className="mono caption">{formatTimestamp(p.predicted_at).display}</td>
                  <td className="mono">{p.model_version}</td>
                  <td className="mono font-semibold">{(p.fraud_probability * 100).toFixed(2)}%</td>
                  <td>
                    <RiskBadge level={p.risk_level} size="sm" />
                  </td>
                  <td className="mono caption">{(p.decision_threshold * 100).toFixed(1)}%</td>
                  <td>
                    {p.predicted_class === 1 ? (
                      <span className="predicted-fraud-tag">Flagged Risk</span>
                    ) : (
                      <span className="predicted-legit-tag">Legitimate</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {/* Case Creation Modal */}
      <Dialog
        isOpen={isCaseModalOpen}
        onClose={() => setIsCaseModalOpen(false)}
        title={`Open Investigation Case for Txn #${tx.id}`}
        description="Creates an auditable investigation case in OPEN status assigned to the analyst triage queue."
      >
        <form
          onSubmit={(e) => {
            e.preventDefault()
            createCaseMutation.mutate(caseDescription)
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div className="panel-subtle" style={{ padding: '12px' }}>
              <div className="caption">Transaction Amount: <strong className="mono">{formatAmount(tx.amount)}</strong></div>
              <div className="caption">Latest Risk Tier: <strong>{latestPred?.risk_level || 'UNKNOWN'}</strong></div>
            </div>

            <Input
              id="case-opening-description"
              label="Opening Notes & Scope (Optional)"
              placeholder="e.g. Flagged high-risk transaction requires verification with cardholder..."
              value={caseDescription}
              onChange={(e) => setCaseDescription(e.target.value)}
              disabled={createCaseMutation.isPending}
            />

            <div className="dialog-footer" style={{ margin: '16px -20px -20px -20px' }}>
              <Button
                variant="secondary"
                size="md"
                onClick={() => setIsCaseModalOpen(false)}
                disabled={createCaseMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                size="md"
                isLoading={createCaseMutation.isPending}
              >
                Confirm & Open Case
              </Button>
            </div>
          </div>
        </form>
      </Dialog>
    </div>
  )
}
