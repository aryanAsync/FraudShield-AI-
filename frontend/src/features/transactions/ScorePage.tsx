import React, { useState, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  AlertCircle,
  Play,
  RotateCcw,
  Info,
  ArrowRight,
  ShieldCheck,
  Calculator,
  FileCode,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import { transactionsApi } from '../../api'
import type {
  BatchScoreRequest,
  BatchScoreResponse,
  ScoreTransactionRequest,
  ScoreTransactionResponse,
} from '../../api/types'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { RiskBadge } from '../../components/risk/RiskBadge'
import { ProbabilityMeter } from '../../components/risk/ProbabilityMeter'
import { ShapBarList } from '../../components/risk/ShapBarList'
import { useToast } from '../../components/ui/Toast'
import { PCA_FEATURES } from '../../lib/constants'
import { formatAmount } from '../../lib/format'
import { parseCsvContent, type CsvValidationResult } from './csvParser'
import './ScorePage.css'

export const ScorePage: React.FC = () => {
  const toast = useToast()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Top-level mode tab: 'csv' (primary) or 'manual' (secondary)
  const [activeTab, setActiveTab] = useState<'csv' | 'manual'>('csv')

  // --- CSV Upload State ---
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [csvResult, setCsvResult] = useState<CsvValidationResult | null>(null)
  const [showErrorRows, setShowErrorRows] = useState(false)
  const [batchThreshold, setBatchThreshold] = useState<string>('')
  const [batchExplainHighRisk, setBatchExplainHighRisk] = useState<boolean>(false)
  const [batchResult, setBatchResult] = useState<BatchScoreResponse | null>(null)

  // --- Manual Entry State (Preserved) ---
  const [time, setTime] = useState<string>('0.0')
  const [amount, setAmount] = useState<string>('100.00')
  const [vFeatures, setVFeatures] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {}
    PCA_FEATURES.forEach((f) => {
      init[f] = '0.0'
    })
    return init
  })
  const [externalReference, setExternalReference] = useState<string>('')
  const [manualExplain, setManualExplain] = useState<boolean>(true)
  const [manualThreshold, setManualThreshold] = useState<string>('')
  const [openGroup, setOpenGroup] = useState<number | null>(1)
  const [showBulkPaste, setShowBulkPaste] = useState(false)
  const [bulkJsonText, setBulkJsonText] = useState('')
  const [bulkError, setBulkError] = useState<string | null>(null)
  const [singleResult, setSingleResult] = useState<ScoreTransactionResponse | null>(null)
  const [singleSubmitError, setSingleSubmitError] = useState<string | null>(null)

  const handleFileSelection = (file: File) => {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      toast.error('Only .csv files are supported.')
      return
    }

    if (file.size > 10 * 1024 * 1024) {
      toast.error('File size exceeds the 10 MB limit.')
      return
    }

    setSelectedFile(file)
    setBatchResult(null)

    const reader = new FileReader()
    reader.onload = (e) => {
      const content = e.target?.result as string
      try {
        const result = parseCsvContent(content)
        setCsvResult(result)
        toast.info(
          `Parsed ${result.validItems.length} valid transactions from ${file.name}.${
            result.hasGroundTruth ? ' Ground-truth labels detected and isolated.' : ''
          }`
        )
      } catch (err: any) {
        setCsvResult(null)
        toast.error(`CSV Validation Error: ${err.message}`)
      }
    }
    reader.onerror = () => {
      toast.error('Failed to read file from disk.')
    }
    reader.readAsText(file)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelection(e.dataTransfer.files[0])
    }
  }

  // --- Batch Score Mutation ---
  const batchScoreMutation = useMutation({
    mutationFn: (payload: BatchScoreRequest) => transactionsApi.batchScore(payload),
    onSuccess: (data) => {
      setBatchResult(data)
      // Invalidate relevant queries so dashboard updates dynamically
      queryClient.invalidateQueries({ queryKey: ['analytics-overview'] })
      queryClient.invalidateQueries({ queryKey: ['analytics-risk-distribution'] })
      queryClient.invalidateQueries({ queryKey: ['analytics-trends'] })
      queryClient.invalidateQueries({ queryKey: ['analytics-page-risk'] })
      queryClient.invalidateQueries({ queryKey: ['analytics-page-trends'] })
      queryClient.invalidateQueries({ queryKey: ['analytics-case-status'] })
      queryClient.invalidateQueries({ queryKey: ['analytics-feature-importance'] })
      queryClient.invalidateQueries({ queryKey: ['transactions-list'] })
      toast.success(
        `Batch scoring complete! ${data.persisted_count} transactions persisted (${data.flagged_fraud_count} flagged fraud).`
      )
    },
    onError: (err: any) => {
      toast.error(err.message || 'Batch scoring failed. Please inspect backend logs.')
    },
  })

  const handleSubmitBatch = () => {
    if (!csvResult || csvResult.validItems.length === 0) {
      toast.error('No valid transactions to score.')
      return
    }

    const payload: BatchScoreRequest = {
      transactions: csvResult.validItems,
      threshold: batchThreshold ? parseFloat(batchThreshold) : undefined,
      explain: batchExplainHighRisk,
    }

    batchScoreMutation.mutate(payload)
  }

  const handleResetCsv = () => {
    setSelectedFile(null)
    setCsvResult(null)
    setBatchResult(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  // --- Single Transaction Manual Handlers ---
  const handleVChange = (feature: string, value: string) => {
    setVFeatures((prev) => ({ ...prev, [feature]: value }))
  }

  const handleApplyBulkJson = () => {
    setBulkError(null)
    try {
      const parsed = JSON.parse(bulkJsonText)
      if (typeof parsed !== 'object' || parsed === null) {
        setBulkError('JSON must be an object with feature key-value pairs.')
        return
      }

      if (parsed.Time !== undefined) setTime(String(parsed.Time))
      if (parsed.Amount !== undefined) setAmount(String(parsed.Amount))
      if (parsed.external_reference) setExternalReference(String(parsed.external_reference))

      setVFeatures((prev) => {
        const next = { ...prev }
        PCA_FEATURES.forEach((f) => {
          if (parsed[f] !== undefined) {
            next[f] = String(parsed[f])
          }
        })
        return next
      })

      setShowBulkPaste(false)
      toast.success('Feature vector inputs populated from JSON.')
    } catch (e: any) {
      setBulkError(`Invalid JSON syntax: ${e.message}`)
    }
  }

  const singleScoreMutation = useMutation({
    mutationFn: (payload: ScoreTransactionRequest) => transactionsApi.score(payload),
    onSuccess: (data) => {
      setSingleResult(data)
      setSingleSubmitError(null)
      queryClient.invalidateQueries({ queryKey: ['transactions-list'] })
      queryClient.invalidateQueries({ queryKey: ['analytics-overview'] })
      queryClient.invalidateQueries({ queryKey: ['analytics-risk-distribution'] })
      toast.success(`Transaction #${data.transaction_id} scored and persisted successfully.`)
    },
    onError: (err: any) => {
      setSingleSubmitError(err.message || 'Scoring failed. Please review input fields.')
      toast.error('Failed to score and persist transaction.')
    },
  })

  const handleSubmitSingle = (e: React.FormEvent) => {
    e.preventDefault()
    setSingleSubmitError(null)

    const parsedTime = parseFloat(time)
    const parsedAmount = parseFloat(amount)

    if (isNaN(parsedTime) || !isFinite(parsedTime)) {
      setSingleSubmitError('Time must be a valid finite number.')
      return
    }
    if (isNaN(parsedAmount) || !isFinite(parsedAmount) || parsedAmount < 0) {
      setSingleSubmitError('Amount must be a non-negative number.')
      return
    }

    const payload: any = {
      Time: parsedTime,
      Amount: parsedAmount,
      explain: manualExplain,
    }

    if (externalReference.trim()) {
      payload.external_reference = externalReference.trim()
    }

    if (manualThreshold.trim()) {
      const parsedThresh = parseFloat(manualThreshold)
      if (!isNaN(parsedThresh) && parsedThresh >= 0 && parsedThresh <= 1) {
        payload.threshold = parsedThresh
      }
    }

    for (const f of PCA_FEATURES) {
      const val = parseFloat(vFeatures[f] || '0')
      if (isNaN(val) || !isFinite(val)) {
        setSingleSubmitError(`Feature ${f} must be a valid finite number.`)
        return
      }
      payload[f] = val
    }

    singleScoreMutation.mutate(payload as ScoreTransactionRequest)
  }

  return (
    <div className="score-page">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Transaction Risk Scoring</h1>
          <p className="caption">
            Upload batch transaction vectors via CSV or manually enter feature inputs to evaluate fraud probability using the deployed Random Forest model.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="tab-pill-group" role="tablist" aria-label="Scoring Mode">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'csv'}
            className={`tab-pill-btn ${activeTab === 'csv' ? 'active' : ''}`}
            onClick={() => setActiveTab('csv')}
          >
            <FileSpreadsheet size={15} />
            <span>CSV Batch Upload (Primary)</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'manual'}
            className={`tab-pill-btn ${activeTab === 'manual' ? 'active' : ''}`}
            onClick={() => setActiveTab('manual')}
          >
            <Calculator size={15} />
            <span>Single Transaction Entry</span>
          </button>
        </div>
      </div>

      {/* ========================================================= */}
      {/* TAB 1: CSV UPLOAD & BATCH SCORING (PRIMARY WORKFLOW)      */}
      {/* ========================================================= */}
      {activeTab === 'csv' && (
        <div className="csv-workflow-container">
          {!batchResult ? (
            <>
              {/* File Dropzone */}
              {!csvResult && (
                <div
                  className={`csv-dropzone ${isDragging ? 'dragging' : ''}`}
                  onDragOver={(e) => {
                    e.preventDefault()
                    setIsDragging(true)
                  }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".csv"
                    style={{ display: 'none' }}
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        handleFileSelection(e.target.files[0])
                      }
                    }}
                  />
                  <div className="dropzone-icon">
                    <UploadCloud size={40} />
                  </div>
                  <h3 className="dropzone-title">Select or drag &amp; drop a CSV file</h3>
                  <p className="caption text-muted">
                    Supports files up to 1,000 transactions (max 10 MB). Requires <code>Time</code>, <code>Amount</code>, and <code>V1</code>–<code>V28</code> columns.
                  </p>
                  <Button variant="secondary" size="sm" type="button">
                    Browse Local File
                  </Button>
                </div>
              )}

              {/* CSV Validation Preview */}
              {csvResult && selectedFile && (
                <div className="csv-preview-panel panel">
                  {/* File Metadata Header */}
                  <div className="preview-top-bar">
                    <div className="file-info-badge">
                      <FileSpreadsheet size={20} className="text-brand-cyan" />
                      <div>
                        <strong className="file-name">{selectedFile.name}</strong>
                        <span className="file-size caption">
                          ({(selectedFile.size / 1024).toFixed(1)} KB) &bull; {csvResult.totalRows} rows in file
                        </span>
                      </div>
                    </div>

                    <Button variant="tertiary" size="sm" leftIcon={<RotateCcw size={14} />} onClick={handleResetCsv}>
                      Change File
                    </Button>
                  </div>

                  {/* Ground Truth Isolation Banner */}
                  {csvResult.hasGroundTruth && (
                    <div className="ground-truth-banner">
                      <ShieldCheck size={18} className="text-brand-emerald" />
                      <div>
                        <strong>Ground-Truth Label ('Class') Detected &amp; Isolated</strong>
                        <p className="caption">
                          The CSV contains ground-truth fraud labels (0/1). These labels have been safely extracted for comparison and <strong>will not be passed to the ML inference model</strong> to maintain strict evaluation integrity.
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Validation Summary Strip */}
                  <div className="validation-summary-grid">
                    <div className="val-stat-box">
                      <span className="caption">TOTAL ROWS</span>
                      <span className="val-stat-num mono">{csvResult.totalRows}</span>
                    </div>
                    <div className="val-stat-box">
                      <span className="caption text-risk-low">VALID SCORABLE ROWS</span>
                      <span className="val-stat-num text-risk-low mono">{csvResult.validItems.length}</span>
                    </div>
                    <div className="val-stat-box">
                      <span className="caption text-risk-high">INVALID / REJECTED ROWS</span>
                      <span className="val-stat-num text-risk-high mono">{csvResult.errors.length}</span>
                    </div>
                  </div>

                  {/* Errors Dropdown (if any) */}
                  {csvResult.errors.length > 0 && (
                    <div className="validation-errors-box">
                      <div className="errors-header" onClick={() => setShowErrorRows(!showErrorRows)}>
                        <div className="error-title-row">
                          <AlertCircle size={16} className="text-risk-high" />
                          <span>{csvResult.errors.length} rows contain validation errors (skipped)</span>
                        </div>
                        <Button variant="tertiary" size="sm">
                          {showErrorRows ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                        </Button>
                      </div>

                      {showErrorRows && (
                        <div className="error-list">
                          {csvResult.errors.slice(0, 10).map((err, idx) => (
                            <div key={idx} className="error-item caption">
                              <span className="mono">Row {err.row}:</span> {err.reason}
                            </div>
                          ))}
                          {csvResult.errors.length > 10 && (
                            <div className="caption text-muted">
                              ...and {csvResult.errors.length - 10} more rows
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {/* First 5 Rows Preview */}
                  <div className="table-preview-section">
                    <h4 className="preview-table-title">
                      Input Feature Vector Preview (First {Math.min(5, csvResult.validItems.length)} of {csvResult.validItems.length} valid rows)
                    </h4>
                    <div className="preview-table-wrapper">
                      <table className="preview-table mono">
                        <thead>
                          <tr>
                            <th>#</th>
                            <th>Time</th>
                            <th>Amount</th>
                            {csvResult.hasGroundTruth && <th className="th-gt">Class (GT)</th>}
                            <th>V1</th>
                            <th>V2</th>
                            <th>V3</th>
                            <th>V4</th>
                            <th>V5</th>
                            <th>...</th>
                            <th>V28</th>
                          </tr>
                        </thead>
                        <tbody>
                          {csvResult.validItems.slice(0, 5).map((row, idx) => (
                            <tr key={idx}>
                              <td>{idx + 1}</td>
                              <td>{row.Time.toFixed(1)}</td>
                              <td>{formatAmount(row.Amount)}</td>
                              {csvResult.hasGroundTruth && (
                                <td className="td-gt">
                                  {csvResult.groundTruthClasses[idx] === 1 ? (
                                    <span className="gt-fraud">1 (Fraud)</span>
                                  ) : (
                                    <span className="gt-clean">0 (Clean)</span>
                                  )}
                                </td>
                              )}
                              <td>{row.V1.toFixed(3)}</td>
                              <td>{row.V2.toFixed(3)}</td>
                              <td>{row.V3.toFixed(3)}</td>
                              <td>{row.V4.toFixed(3)}</td>
                              <td>{row.V5.toFixed(3)}</td>
                              <td>...</td>
                              <td>{row.V28.toFixed(3)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Batch Scoring Submission Controls */}
                  <div className="submission-controls-panel">
                    <div className="controls-options">
                      <div className="control-item">
                        <label className="caption">Decision Threshold (Optional override)</label>
                        <Input
                          type="number"
                          step="0.01"
                          min="0"
                          max="1"
                          placeholder="Default: 0.56"
                          value={batchThreshold}
                          onChange={(e) => setBatchThreshold(e.target.value)}
                          className="mono"
                        />
                      </div>
                      <div className="control-checkbox">
                        <label className="checkbox-label">
                          <input
                            type="checkbox"
                            checked={batchExplainHighRisk}
                            onChange={(e) => setBatchExplainHighRisk(e.target.checked)}
                          />
                          <span>Generate SHAP explanations for High-Risk items during batch</span>
                        </label>
                      </div>
                    </div>

                    <div className="submit-action-row">
                      <Button
                        variant="primary"
                        size="lg"
                        leftIcon={<Play size={18} />}
                        onClick={handleSubmitBatch}
                        disabled={batchScoreMutation.isPending || csvResult.validItems.length === 0}
                      >
                        {batchScoreMutation.isPending
                          ? 'Evaluating & Persisting Batch...'
                          : `Score & Persist ${csvResult.validItems.length} Transactions`}
                      </Button>
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : (
            /* ========================================================= */
            /* BATCH RESULTS SUMMARY CARD                                */
            /* ========================================================= */
            <div className="batch-results-panel panel">
              <div className="results-header-line">
                <div className="results-icon-badge">
                  <CheckCircle2 size={32} className="text-brand-emerald" />
                </div>
                <div>
                  <h2 className="results-title">Batch Scoring &amp; Persistence Complete</h2>
                  <p className="caption">
                    All predictions have been calculated with the deployed Random Forest model and permanently saved in PostgreSQL.
                  </p>
                </div>
              </div>

              {/* Reconciled Result Counts */}
              <div className="result-kpis-grid">
                <div className="r-kpi">
                  <span className="caption">TRANSACTIONS RECEIVED</span>
                  <span className="r-kpi-val mono">{batchResult.total_received}</span>
                </div>
                <div className="r-kpi">
                  <span className="caption">SUCCESSFULLY PERSISTED</span>
                  <span className="r-kpi-val text-brand-emerald mono">{batchResult.persisted_count}</span>
                </div>
                <div className="r-kpi">
                  <span className="caption text-risk-high">PREDICTED FRAUD (CLASS 1)</span>
                  <span className="r-kpi-val text-risk-high mono">{batchResult.flagged_fraud_count}</span>
                </div>
                <div className="r-kpi">
                  <span className="caption">LOW RISK</span>
                  <span className="r-kpi-val text-risk-low mono">{batchResult.low_risk_count}</span>
                </div>
                <div className="r-kpi">
                  <span className="caption">MEDIUM RISK</span>
                  <span className="r-kpi-val text-risk-medium mono">{batchResult.medium_risk_count}</span>
                </div>
                <div className="r-kpi">
                  <span className="caption">HIGH RISK</span>
                  <span className="r-kpi-val text-risk-high mono">{batchResult.high_risk_count}</span>
                </div>
              </div>

              {/* Dynamic Flow Notice */}
              <div className="flow-notice-box caption">
                <Info size={16} className="text-brand-cyan" />
                <span>
                  The Executive Dashboard has been notified and updated with these new transactions. Navigating back to the Dashboard or Transactions Explorer will show your live data immediately.
                </span>
              </div>

              {/* Navigation Action Buttons */}
              <div className="results-action-row">
                <Button
                  variant="primary"
                  size="md"
                  rightIcon={<ArrowRight size={16} />}
                  onClick={() => navigate('/transactions')}
                >
                  View in Transactions Explorer
                </Button>
                <Button
                  variant="secondary"
                  size="md"
                  onClick={() => navigate('/overview')}
                >
                  View Executive Dashboard
                </Button>
                <Button variant="tertiary" size="md" onClick={handleResetCsv}>
                  Score Another CSV File
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB 2: MANUAL SINGLE TRANSACTION ENTRY (PRESERVED)        */}
      {/* ========================================================= */}
      {activeTab === 'manual' && (
        <>
          {showBulkPaste && (
            <div className="bulk-paste-panel panel">
              <div className="bulk-header">
                <div>
                  <h3 className="section-title">Bulk Feature Vector Paste</h3>
                  <p className="caption">
                    Paste a JSON object with <code>Time</code>, <code>Amount</code>, and <code>V1</code> through <code>V28</code> keys.
                  </p>
                </div>
                <Button variant="tertiary" size="sm" onClick={() => setShowBulkPaste(false)}>
                  Close
                </Button>
              </div>
              <textarea
                className="bulk-textarea mono"
                rows={8}
                value={bulkJsonText}
                onChange={(e) => setBulkJsonText(e.target.value)}
                placeholder={'{\n  "Time": 406.0,\n  "Amount": 149.99,\n  "V1": -2.312,\n  ...\n}'}
              />
              {bulkError && <div className="caption text-risk-high">{bulkError}</div>}
              <div className="bulk-actions">
                <Button variant="primary" size="sm" onClick={handleApplyBulkJson}>
                  Apply JSON to Form
                </Button>
              </div>
            </div>
          )}

          <div className="score-layout-grid">
            {/* Form */}
            <form onSubmit={handleSubmitSingle} className="score-form panel">
              <div className="form-header-row">
                <div>
                  <h2 className="section-title">Manual Transaction Input</h2>
                  <p className="caption">Single-record inference and database persistence.</p>
                </div>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  leftIcon={<FileCode size={14} />}
                  onClick={() => setShowBulkPaste(!showBulkPaste)}
                >
                  Paste JSON Vector
                </Button>
              </div>

              {singleSubmitError && (
                <div className="submit-error-banner caption">
                  <AlertCircle size={16} />
                  <span>{singleSubmitError}</span>
                </div>
              )}

              {/* Core Features */}
              <div className="form-section-header">
                <h3 className="form-section-title">Core Transaction Properties</h3>
              </div>
              <div className="core-inputs-grid">
                <Input
                  label="Dataset Time (Seconds)"
                  type="number"
                  step="0.1"
                  required
                  value={time}
                  onChange={(e) => setTime(e.target.value)}
                  className="mono tabular-nums"
                />
                <Input
                  label="Transaction Amount"
                  type="number"
                  step="0.01"
                  min="0"
                  required
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="mono tabular-nums"
                />
              </div>

              <div className="core-inputs-grid">
                <Input
                  label="External Reference (Optional Idempotency Key)"
                  type="text"
                  placeholder="e.g. TXN-894102"
                  value={externalReference}
                  onChange={(e) => setExternalReference(e.target.value)}
                  className="mono"
                />
                <Input
                  label="Decision Threshold Override (0.00 - 1.00)"
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  placeholder="Default (0.56)"
                  value={manualThreshold}
                  onChange={(e) => setManualThreshold(e.target.value)}
                  className="mono"
                />
              </div>

              <div className="control-checkbox" style={{ marginTop: '4px' }}>
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={manualExplain}
                    onChange={(e) => setManualExplain(e.target.checked)}
                  />
                  <span>Generate SHAP feature attribution explanation for this transaction</span>
                </label>
              </div>

              {/* PCA Features */}
              <div className="form-section-header">
                <h3 className="form-section-title">Anonymized PCA Vectors (V1 - V28)</h3>
                <p className="caption text-muted">
                  Components derived via Principal Component Analysis to preserve confidentiality.
                </p>
              </div>

              {/* Group 1: V1 - V10 */}
              <div className="accordion-block border-default">
                <div className="accordion-header" onClick={() => setOpenGroup(openGroup === 1 ? null : 1)}>
                  <span>Features V1 through V10</span>
                  {openGroup === 1 ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </div>
                {openGroup === 1 && (
                  <div className="v-features-grid">
                    {PCA_FEATURES.slice(0, 10).map((f) => (
                      <div key={f} className="v-input-cell">
                        <label className="caption mono">{f}</label>
                        <input
                          type="number"
                          step="0.0001"
                          value={vFeatures[f] || '0.0'}
                          onChange={(e) => handleVChange(f, e.target.value)}
                          className="v-input mono tabular-nums"
                        />
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Group 2: V11 - V20 */}
              <div className="accordion-block border-default">
                <div className="accordion-header" onClick={() => setOpenGroup(openGroup === 2 ? null : 2)}>
                  <span>Features V11 through V20</span>
                  {openGroup === 2 ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </div>
                {openGroup === 2 && (
                  <div className="v-features-grid">
                    {PCA_FEATURES.slice(10, 20).map((f) => (
                      <div key={f} className="v-input-cell">
                        <label className="caption mono">{f}</label>
                        <input
                          type="number"
                          step="0.0001"
                          value={vFeatures[f] || '0.0'}
                          onChange={(e) => handleVChange(f, e.target.value)}
                          className="v-input mono tabular-nums"
                        />
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Group 3: V21 - V28 */}
              <div className="accordion-block border-default">
                <div className="accordion-header" onClick={() => setOpenGroup(openGroup === 3 ? null : 3)}>
                  <span>Features V21 through V28</span>
                  {openGroup === 3 ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </div>
                {openGroup === 3 && (
                  <div className="v-features-grid">
                    {PCA_FEATURES.slice(20, 28).map((f) => (
                      <div key={f} className="v-input-cell">
                        <label className="caption mono">{f}</label>
                        <input
                          type="number"
                          step="0.0001"
                          value={vFeatures[f] || '0.0'}
                          onChange={(e) => handleVChange(f, e.target.value)}
                          className="v-input mono tabular-nums"
                        />
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Submit Buttons */}
              <div className="form-submit-row">
                <Button
                  type="submit"
                  variant="primary"
                  size="md"
                  leftIcon={<Play size={16} />}
                  disabled={singleScoreMutation.isPending}
                >
                  {singleScoreMutation.isPending ? 'Scoring & Persisting...' : 'Score Single Transaction'}
                </Button>
              </div>
            </form>

            {/* Single Result Column */}
            <div className="score-result-panel panel">
              <h2 className="section-title">Prediction Result</h2>
              {singleResult ? (
                <div className="result-content-body">
                  <div className="result-summary-card">
                    <div className="result-card-top">
                      <div>
                        <span className="caption">TRANSACTION ID</span>
                        <div className="mono font-semibold">#{singleResult.transaction_id}</div>
                      </div>
                      <RiskBadge level={singleResult.prediction.risk_level} size="md" />
                    </div>

                    <div className="result-metric-row">
                      <div className="res-stat">
                        <span className="caption">MODEL RISK SCORE</span>
                        <div className="mono res-stat-val">
                          {singleResult.prediction.risk_score.toFixed(1)} / 100
                        </div>
                      </div>
                      <div className="res-stat">
                        <span className="caption">PREDICTED DECISION</span>
                        <div className="mono res-stat-val">
                          {singleResult.prediction.predicted_class === 1 ? 'FRAUD (1)' : 'LEGITIMATE (0)'}
                        </div>
                      </div>
                    </div>

                    <ProbabilityMeter
                      probability={singleResult.prediction.fraud_probability}
                      threshold={singleResult.prediction.decision_threshold}
                      size="md"
                    />

                    <div className="view-detail-link-box">
                      <Link
                        to={`/transactions/${singleResult.transaction_id}`}
                        className="btn-view-detail"
                      >
                        <span>Open Full Transaction Record</span>
                        <ArrowRight size={14} />
                      </Link>
                    </div>
                  </div>

                  {singleResult.prediction.explanation && (
                    <ShapBarList explanations={singleResult.prediction.explanation as any} />
                  )}
                </div>
              ) : (
                <div className="empty-result-card caption text-muted">
                  <Info size={24} className="text-muted" />
                  <p>Submit a transaction vector to view the real-time ML prediction and SHAP explanation.</p>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
