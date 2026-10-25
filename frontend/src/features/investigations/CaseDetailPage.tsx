import React, { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  Lock,
  Send,
  UserCheck,
  AlertTriangle,
  Info,
  ShieldAlert,
  ExternalLink,
} from 'lucide-react'
import { casesApi, usersApi } from '../../api'
import type { CaseStatus } from '../../api/types'
import { StatusBadge } from '../../components/risk/StatusBadge'
import { RiskBadge } from '../../components/risk/RiskBadge'
import { ProbabilityMeter } from '../../components/risk/ProbabilityMeter'
import { Button } from '../../components/ui/Button'
import { Dialog } from '../../components/ui/Dialog'
import { Skeleton } from '../../components/ui/Skeleton'
import { ErrorState } from '../../components/feedback/ErrorState'
import { useToast } from '../../components/ui/Toast'
import { useAuth } from '../../auth/AuthContext'
import { formatAmount, formatTimestamp } from '../../lib/format'
import { getAvailableTransitions, type StateTransitionOption } from '../../lib/caseTransitions'
import { MODEL_ESTIMATE_NOTICE } from '../../lib/constants'
import './Investigations.css'

export const CaseDetailPage: React.FC = () => {
  const { caseId } = useParams<{ caseId: string }>()
  const cId = parseInt(caseId || '0', 10)
  const queryClient = useQueryClient()
  const toast = useToast()
  const { user, role } = useAuth()

  const [noteBody, setNoteBody] = useState('')
  const [selectedTransition, setSelectedTransition] = useState<StateTransitionOption | null>(null)
  const [isTransitionModalOpen, setIsTransitionModalOpen] = useState(false)

  const isAdmin = role === 'ADMIN'
  const isAuditor = role === 'AUDITOR'
  const isAnalyst = role === 'ANALYST'

  // 1. Fetch Case Details
  const caseQuery = useQuery({
    queryKey: ['case-detail', cId],
    queryFn: () => casesApi.getById(cId),
    enabled: cId > 0,
  })

  // 2. Fetch Analysts list (if admin, to populate assignee combobox)
  const analystsQuery = useQuery({
    queryKey: ['analysts-for-assignment'],
    queryFn: () => usersApi.list({ role: 'ANALYST', is_active: true, page_size: 100 }),
    enabled: isAdmin,
  })

  // 3. Add Note Mutation
  const addNoteMutation = useMutation({
    mutationFn: (body: string) => casesApi.addNote(cId, { body }),
    onSuccess: () => {
      setNoteBody('')
      toast.success('Investigation note recorded.')
      queryClient.invalidateQueries({ queryKey: ['case-detail', cId] })
      queryClient.invalidateQueries({ queryKey: ['audit-logs'] })
    },
    onError: (err: any) => {
      toast.error(err?.message || 'Failed to record investigation note.')
    },
  })

  // 4. Update Case Mutation (Status & Assignment)
  const updateCaseMutation = useMutation({
    mutationFn: (payload: { status?: CaseStatus; assigned_user_id?: number | null }) =>
      casesApi.update(cId, payload),
    onSuccess: (updated) => {
      toast.success(`Case updated to ${updated.status}.`)
      setIsTransitionModalOpen(false)
      setSelectedTransition(null)
      queryClient.invalidateQueries({ queryKey: ['case-detail', cId] })
      queryClient.invalidateQueries({ queryKey: ['cases-list'] })
      queryClient.invalidateQueries({ queryKey: ['analytics-overview'] })
      queryClient.invalidateQueries({ queryKey: ['analytics-case-status'] })
    },
    onError: (err: any) => {
      toast.error(err?.message || 'Case update rejected by server.')
    },
  })

  const currentCase = caseQuery.data

  const handleAddNote = (e: React.FormEvent) => {
    e.preventDefault()
    const clean = noteBody.trim()
    if (!clean) return
    addNoteMutation.mutate(clean)
  }

  const handleConfirmTransition = () => {
    if (!selectedTransition) return
    updateCaseMutation.mutate({ status: selectedTransition.to })
  }

  const handleAssignToMe = () => {
    if (!user) return
    updateCaseMutation.mutate({ assigned_user_id: user.id })
  }

  const handleAdminAssign = (targetIdStr: string) => {
    if (targetIdStr === 'unassign') {
      updateCaseMutation.mutate({ assigned_user_id: null })
    } else if (targetIdStr) {
      updateCaseMutation.mutate({ assigned_user_id: parseInt(targetIdStr, 10) })
    }
  }

  if (caseQuery.isLoading) {
    return (
      <div className="case-detail-page">
        <Skeleton height="36px" width="280px" />
        <div className="case-detail-2col-layout" style={{ marginTop: '20px' }}>
          <Skeleton height="500px" />
          <Skeleton height="400px" />
        </div>
      </div>
    )
  }

  if (caseQuery.isError || !currentCase) {
    return (
      <div className="case-detail-page">
        <Link to="/investigations" className="back-link">
          <ArrowLeft size={16} />
          <span>Back to Investigation Queue</span>
        </Link>
        <ErrorState
          title={`Investigation Case #${cId} Not Found`}
          error={caseQuery.error || 'This investigation case does not exist or access is restricted.'}
          onRetry={() => caseQuery.refetch()}
        />
      </div>
    )
  }

  const isClosed = currentCase.status === 'CLOSED'
  const availableTransitions = getAvailableTransitions(currentCase.status)
  const isAssignedToMe = user && currentCase.assigned_user_id === user.id
  const canAddNotes = !isAuditor && !isClosed && (isAdmin || isAssignedToMe || currentCase.assigned_user_id === null)

  return (
    <div className="case-detail-page">
      {/* Back link */}
      <Link to="/investigations" className="back-link">
        <ArrowLeft size={16} />
        <span>Back to Investigation Queue</span>
      </Link>

      {/* Case Header */}
      <div className="case-header-panel panel">
        <div className="case-header-left">
          <div className="case-id-status-row">
            <h1 className="case-id-title mono">Case #{currentCase.id}</h1>
            <StatusBadge status={currentCase.status} size="md" />
            {isAuditor && (
              <span className="auditor-readonly-badge caption">
                Read-Only (Auditor)
              </span>
            )}
          </div>
          <div className="case-meta-row caption">
            <span>Opened: {formatTimestamp(currentCase.created_at).display}</span>
            <span>&bull;</span>
            <span>Updated: {formatTimestamp(currentCase.updated_at).display}</span>
            {currentCase.resolved_at && (
              <>
                <span>&bull;</span>
                <span>Resolved: {formatTimestamp(currentCase.resolved_at).display}</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Two-Pane Workspace Layout */}
      <div className="case-detail-2col-layout">
        {/* Left Pane (≈60%): Activity Timeline & Notes */}
        <section className="timeline-pane panel" aria-labelledby="timeline-heading">
          <div className="timeline-header">
            <div className="timeline-title-group">
              <h2 id="timeline-heading" className="section-title">
                Investigation Notes & Activity Timeline
              </h2>
              <div className="timeline-immutable-badge caption">
                <Lock size={12} />
                <span>Notes are immutable and recorded in chronological sequence</span>
              </div>
            </div>
          </div>

          {/* Timeline Feed */}
          <div className="timeline-feed" role="list">
            {/* Opening case event */}
            <div className="timeline-item" role="listitem">
              <div className="timeline-dot" />
              <div className="timeline-card panel-subtle">
                <div className="timeline-card-header">
                  <div className="author-info">
                    <span className="author-name font-semibold">System Case Triage</span>
                    <span className="role-tag">INITIAL</span>
                  </div>
                  <span className="mono caption">{formatTimestamp(currentCase.created_at).display}</span>
                </div>
                <div className="timeline-card-body">
                  {currentCase.description || 'Investigation case initialized for transaction review.'}
                </div>
              </div>
            </div>

            {/* Note items */}
            {currentCase.case_notes.map((note) => (
              <div key={note.id} className="timeline-item" role="listitem">
                <div className="timeline-dot note-dot" />
                <div className="timeline-card panel-subtle">
                  <div className="timeline-card-header">
                    <div className="author-info">
                      <span className="author-name font-semibold">{note.author_name}</span>
                      <span className="role-tag">{note.author_role}</span>
                    </div>
                    <span className="mono caption">{formatTimestamp(note.created_at).display}</span>
                  </div>
                  <div className="timeline-card-body whitespace-pre-wrap">{note.body}</div>
                </div>
              </div>
            ))}
          </div>

          {/* Note Composer */}
          <div className="note-composer-container">
            {isAuditor ? (
              <div className="composer-disabled-banner caption">
                Auditor accounts have read-only access. Notes cannot be added.
              </div>
            ) : isClosed ? (
              <div className="composer-disabled-banner caption">
                <Lock size={14} />
                <span>This investigation case is closed. Notes can no longer be added.</span>
              </div>
            ) : !canAddNotes ? (
              <div className="composer-disabled-banner caption">
                This case is assigned to another analyst. Claim or reassign the case to add notes.
              </div>
            ) : (
              <form onSubmit={handleAddNote} className="note-composer-form">
                <label htmlFor="case-note-input" className="caption font-semibold">
                  Record Investigation Findings:
                </label>
                <textarea
                  id="case-note-input"
                  className="note-textarea"
                  rows={3}
                  placeholder="Record findings, communications with cardholder, card status..."
                  value={noteBody}
                  onChange={(e) => setNoteBody(e.target.value)}
                  disabled={addNoteMutation.isPending}
                />
                <div className="note-composer-actions">
                  <span className="caption char-counter">{noteBody.length} / 5000</span>
                  <Button
                    type="submit"
                    variant="primary"
                    size="sm"
                    disabled={!noteBody.trim() || addNoteMutation.isPending}
                    isLoading={addNoteMutation.isPending}
                    rightIcon={<Send size={14} />}
                  >
                    Add Note
                  </Button>
                </div>
              </form>
            )}
          </div>
        </section>

        {/* Right Pane (≈40%): Context Rail */}
        <aside className="context-rail" aria-label="Investigation Context Rail">
          {/* Status Transitions Panel */}
          <div className="rail-panel panel">
            <h3 className="rail-panel-title">Case Actions & Adjudication</h3>

            {isAuditor ? (
              <p className="caption">Auditor role is read-only. Status transitions are restricted.</p>
            ) : isClosed ? (
              <div className="terminal-case-notice panel-subtle caption">
                <Lock size={14} />
                <span>Case is in terminal CLOSED status. No further state transitions are permitted.</span>
              </div>
            ) : availableTransitions.length > 0 ? (
              <div className="transition-buttons-list">
                {availableTransitions.map((t) => (
                  <Button
                    key={t.to}
                    variant={t.variant}
                    size="md"
                    className="transition-btn"
                    onClick={() => {
                      setSelectedTransition(t)
                      setIsTransitionModalOpen(true)
                    }}
                  >
                    {t.label}
                  </Button>
                ))}
              </div>
            ) : (
              <p className="caption">No transitions available from current state.</p>
            )}
          </div>

          {/* Assignment Panel */}
          <div className="rail-panel panel">
            <h3 className="rail-panel-title">Analyst Assignment</h3>
            <div className="assignment-status-row">
              <span className="caption">Current Assignee:</span>
              <strong className="mono">
                {currentCase.assigned_user?.name || currentCase.assigned_to || 'Unassigned'}
              </strong>
            </div>

            {!isAuditor && !isClosed && (
              <div className="assignment-controls">
                {isAnalyst && !isAssignedToMe && (
                  <Button
                    variant="secondary"
                    size="sm"
                    leftIcon={<UserCheck size={14} />}
                    onClick={handleAssignToMe}
                    isLoading={updateCaseMutation.isPending}
                  >
                    Claim Case (Assign to Me)
                  </Button>
                )}

                {isAdmin && (
                  <div className="admin-assign-row">
                    <label htmlFor="admin-assignee-select" className="caption">
                      Assign to Analyst:
                    </label>
                    <select
                      id="admin-assignee-select"
                      className="filter-select"
                      value={currentCase.assigned_user_id ? String(currentCase.assigned_user_id) : ''}
                      onChange={(e) => handleAdminAssign(e.target.value)}
                      disabled={updateCaseMutation.isPending}
                    >
                      <option value="unassign">Unassign Case</option>
                      {analystsQuery.data?.items.map((analyst) => (
                        <option key={analyst.id} value={String(analyst.id)}>
                          {analyst.name} ({analyst.email})
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Linked Transaction Context */}
          {currentCase.transaction && (
            <div className="rail-panel panel">
              <div className="rail-panel-header">
                <h3 className="rail-panel-title">Linked Transaction</h3>
                <Link
                  to={`/transactions/${currentCase.transaction_id}`}
                  className="widget-action-link caption"
                >
                  <span>Inspect</span>
                  <ExternalLink size={13} />
                </Link>
              </div>

              <div className="linked-txn-summary">
                <div className="summary-row">
                  <span className="caption">Txn ID:</span>
                  <span className="mono font-semibold">#{currentCase.transaction.id}</span>
                </div>
                <div className="summary-row">
                  <span className="caption">Amount:</span>
                  <span className="mono font-semibold tabular-nums">
                    {formatAmount(currentCase.transaction.amount)}
                  </span>
                </div>
                <div className="summary-row">
                  <span className="caption">Model Risk:</span>
                  <RiskBadge level={currentCase.latest_prediction?.risk_level} size="sm" />
                </div>
                <div className="summary-row">
                  <span className="caption">Fraud Probability:</span>
                  <span className="mono">
                    {currentCase.latest_prediction ? (
                      <ProbabilityMeter
                        probability={currentCase.latest_prediction.fraud_probability}
                        threshold={currentCase.latest_prediction.decision_threshold}
                        size="sm"
                      />
                    ) : (
                      '—'
                    )}
                  </span>
                </div>
              </div>

              <div className="model-notice-banner caption" style={{ marginTop: '12px' }}>
                <Info size={13} className="notice-icon" />
                <span>{MODEL_ESTIMATE_NOTICE}</span>
              </div>
            </div>
          )}
        </aside>
      </div>

      {/* Transition Confirmation Dialog */}
      <Dialog
        isOpen={isTransitionModalOpen}
        onClose={() => setIsTransitionModalOpen(false)}
        title={selectedTransition?.label || 'Confirm Case State Transition'}
        description={`Transitioning case status from ${currentCase.status} → ${selectedTransition?.to}.`}
      >
        <div className="transition-modal-body">
          <p className="caption">{selectedTransition?.description}</p>

          {selectedTransition?.isDetermination && (
            <div className="determination-notice panel-subtle">
              <ShieldAlert size={18} className="text-danger" />
              <p className="caption">
                <strong>Attention:</strong> This action records a permanent human adjudication outcome for
                this financial transaction.
              </p>
            </div>
          )}

          {selectedTransition?.isTerminal && (
            <div className="terminal-warning panel-subtle">
              <AlertTriangle size={18} className="text-danger" />
              <p className="caption">
                <strong>Warning:</strong> Moving a case to CLOSED is irreversible. Once closed, no further
                notes or state transitions can be recorded.
              </p>
            </div>
          )}

          <div className="dialog-footer" style={{ margin: '20px -20px -20px -20px' }}>
            <Button
              variant="secondary"
              size="md"
              onClick={() => setIsTransitionModalOpen(false)}
              disabled={updateCaseMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              variant={selectedTransition?.variant === 'danger' ? 'danger' : 'primary'}
              size="md"
              onClick={handleConfirmTransition}
              isLoading={updateCaseMutation.isPending}
            >
              Confirm Transition
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  )
}
