/**
 * FraudShield AI — Frontend TypeScript Types
 * Strictly aligned with FastAPI Backend Models and OpenAPI 3.1.0 Specification.
 */

export type UserRole = 'ANALYST' | 'ADMIN' | 'AUDITOR';

export type CaseStatus =
  | 'OPEN'
  | 'IN_REVIEW'
  | 'CONFIRMED_FRAUD'
  | 'LEGITIMATE'
  | 'CLOSED';

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH';

// --- Auth & User ---
export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in_minutes: number;
  user_id: number;
  role: UserRole;
  name: string;
  email: string;
}

export interface UserResponse {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
}

export interface UserCreateRequest {
  name: string;
  email: string;
  password: string;
  role: UserRole;
}

export interface UserUpdateRequest {
  name?: string;
  role?: UserRole;
  is_active?: boolean;
  password?: string;
}

export interface PaginatedUsersResponse {
  items: UserResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// --- Predictions & SHAP ---
export interface FeatureAttribution {
  feature: string;
  attribution: number;
  value: number;
}

export interface PredictionRecordResponse {
  id: number;
  transaction_id: number;
  fraud_probability: number;
  risk_score: number;
  predicted_class: number;
  risk_level: RiskLevel;
  decision_threshold: number;
  model_version: string;
  explanation: FeatureAttribution[] | null;
  predicted_at: string;
}

// --- Transactions ---
export interface ScoreTransactionRequest {
  Time: number;
  Amount: number;
  V1: number;
  V2: number;
  V3: number;
  V4: number;
  V5: number;
  V6: number;
  V7: number;
  V8: number;
  V9: number;
  V10: number;
  V11: number;
  V12: number;
  V13: number;
  V14: number;
  V15: number;
  V16: number;
  V17: number;
  V18: number;
  V19: number;
  V20: number;
  V21: number;
  V22: number;
  V23: number;
  V24: number;
  V25: number;
  V26: number;
  V27: number;
  V28: number;
  external_reference?: string;
  submitted_by?: string;
  explain?: boolean;
  threshold?: number;
}

export interface ScoreTransactionResponse {
  transaction_id: number;
  external_reference: string | null;
  transaction_time: number;
  amount: number;
  submitted_by: string | null;
  created_at: string;
  prediction: PredictionRecordResponse;
}

export interface TransactionSummaryResponse {
  id: number;
  external_reference: string | null;
  transaction_time: number;
  amount: number;
  submitted_by: string | null;
  created_at: string;
  latest_prediction: PredictionRecordResponse | null;
}

export interface TransactionDetailResponse {
  id: number;
  external_reference: string | null;
  transaction_time: number;
  amount: number;
  features: Record<string, number>;
  submitted_by: string | null;
  created_at: string;
  latest_prediction: PredictionRecordResponse | null;
  predictions_count: number;
}

export interface PaginatedTransactionsResponse {
  items: TransactionSummaryResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PredictionHistoryResponse {
  transaction_id: number;
  total_evaluations: number;
  predictions: PredictionRecordResponse[];
}

// --- Cases & Notes ---
export interface CaseAssignedUserResponse {
  id: number;
  name: string;
  email: string;
  role: string;
}

export interface CaseTransactionSummary {
  id: number;
  amount: number;
  transaction_time: number;
  external_reference: string | null;
  submitted_by: string | null;
  created_at: string;
}

export interface CasePredictionSummary {
  id: number;
  risk_score: number;
  fraud_probability: number;
  predicted_class: number;
  risk_level: string;
  decision_threshold: number;
  model_version: string;
  predicted_at: string;
}

export interface CaseNoteResponse {
  id: number;
  case_id: number;
  author_id: number | null;
  author_name: string;
  author_email: string;
  author_role: string;
  body: string;
  created_at: string;
}

export interface CaseResponse {
  id: number;
  transaction_id: number;
  status: CaseStatus;
  assigned_user_id: number | null;
  assigned_to: string | null;
  description: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  assigned_user: CaseAssignedUserResponse | null;
  transaction: CaseTransactionSummary | null;
  latest_prediction: CasePredictionSummary | null;
}

export interface CaseDetailResponse extends CaseResponse {
  case_notes: CaseNoteResponse[];
}

export interface PaginatedCasesResponse {
  items: CaseResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PaginatedCaseNotesResponse {
  items: CaseNoteResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CaseCreateRequest {
  transaction_id: number;
  description?: string;
}

export interface CaseUpdateRequest {
  status?: CaseStatus;
  assigned_user_id?: number | null;
  description?: string;
}

export interface CaseNoteCreateRequest {
  body: string;
}

// --- Audit Logs ---
export interface AuditLogResponse {
  id: number;
  actor_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  details: Record<string, any> | null;
  created_at: string;
}

export interface PaginatedAuditLogsResponse {
  items: AuditLogResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// --- Analytics ---
export interface AnalyticsFilterSummary {
  start_date: string | null;
  end_date: string | null;
}

export interface OverviewTransactionsSummary {
  total_transactions: number;
  transactions_with_predictions: number;
  predicted_fraud_count: number;
  predicted_legitimate_count: number;
  predicted_fraud_percentage: number;
}

export interface OverviewPredictionsSummary {
  total_predictions: number;
}

export interface OverviewRiskSummary {
  average_risk_score: number;
  average_fraud_probability: number;
  high_risk_transactions: number;
  medium_risk_transactions: number;
  low_risk_transactions: number;
}

export interface OverviewCasesSummary {
  total_cases: number;
  open: number;
  in_review: number;
  confirmed_fraud: number;
  legitimate: number;
  closed: number;
  unresolved: number;
  resolved: number;
}

export interface AnalyticsOverviewResponse {
  filters: AnalyticsFilterSummary;
  transactions: OverviewTransactionsSummary;
  predictions: OverviewPredictionsSummary;
  risk: OverviewRiskSummary;
  cases: OverviewCasesSummary;
}

export interface RiskDistributionItem {
  risk_level: RiskLevel;
  count: number;
  percentage: number;
}

export interface ClassificationDistributionSummary {
  predicted_fraud_count: number;
  predicted_fraud_percentage: number;
  predicted_legitimate_count: number;
  predicted_legitimate_percentage: number;
}

export interface RiskDistributionResponse {
  total_transactions: number;
  items: RiskDistributionItem[];
  classification: ClassificationDistributionSummary;
}

export interface TrendBucketItem {
  timestamp: string;
  prediction_count: number;
  distinct_transactions: number;
  predicted_fraud_count: number;
  predicted_legitimate_count: number;
  high_risk_count: number;
  average_risk_score: number;
}

export interface AnalyticsTrendsResponse {
  interval: 'hour' | 'day';
  metrics: Record<string, string>;
  items: TrendBucketItem[];
}

export interface CaseStatusDistributionItem {
  status: CaseStatus;
  count: number;
  percentage: number;
}

export interface CaseStatusSummary {
  assigned_count: number;
  unassigned_count: number;
  unresolved_count: number;
  resolved_fraud_count: number;
  resolved_legitimate_count: number;
  average_resolution_time_seconds: number | null;
}

export interface CaseStatusDistributionResponse {
  total_cases: number;
  items: CaseStatusDistributionItem[];
  summary: CaseStatusSummary;
}

export interface FeatureImportanceItem {
  rank: number;
  feature: string;
  mean_absolute_attribution: number;
  sample_count: number;
}

export interface FeatureImportanceResponse {
  sample_size: number;
  target_risk_level: RiskLevel | null;
  features: FeatureImportanceItem[];
  disclaimer: string;
}

// --- Health ---
export interface HealthResponse {
  status: string;
  model_loaded: boolean;
  model_version: string | null;
  model_type: string | null;
  environment: string;
}

// --- API Errors ---
export interface ApiValidationErrorDetail {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export interface ApiErrorPayload {
  error?: string;
  message?: string;
  detail?: string | ApiValidationErrorDetail[];
  details?: ApiValidationErrorDetail[];
}

// --- Batch Transaction Scoring ---
export interface BatchScoreTransactionItem {
  Time: number;
  Amount: number;
  V1: number;
  V2: number;
  V3: number;
  V4: number;
  V5: number;
  V6: number;
  V7: number;
  V8: number;
  V9: number;
  V10: number;
  V11: number;
  V12: number;
  V13: number;
  V14: number;
  V15: number;
  V16: number;
  V17: number;
  V18: number;
  V19: number;
  V20: number;
  V21: number;
  V22: number;
  V23: number;
  V24: number;
  V25: number;
  V26: number;
  V27: number;
  V28: number;
  external_reference?: string;
}

export interface BatchScoreRequest {
  transactions: BatchScoreTransactionItem[];
  threshold?: number;
  explain?: boolean;
}

export interface BatchScoreResponse {
  total_received: number;
  persisted_count: number;
  flagged_fraud_count: number;
  low_risk_count: number;
  medium_risk_count: number;
  high_risk_count: number;
  created_transaction_ids: number[];
}

// --- Model Evaluation & Governance ---
export interface ConfusionMatrixData {
  true_negatives: number;
  false_positives: number;
  false_negatives: number;
  true_positives: number;
}

export interface ModelMetricsData {
  threshold: number;
  precision: number;
  recall: number;
  f1_score: number;
  pr_auc: number;
  roc_auc: number;
  confusion_matrix: ConfusionMatrixData;
  cost_index?: number | null;
}

export interface EvaluatedModelItem {
  model_name: string;
  model_version: string;
  model_type: string;
  is_deployed: boolean;
  status_label: string;
  optimal_threshold: number;
  selected_threshold: number;
  validation_metrics: ModelMetricsData;
  test_metrics: ModelMetricsData | null;
  hyperparameters: Record<string, any>;
  preprocessing: string;
  training_dataset_description: string;
}

export interface ModelEvaluationResponse {
  deployed_model: EvaluatedModelItem;
  baseline_model: EvaluatedModelItem;
  candidate_models?: EvaluatedModelItem[];
  evaluation_timestamp: string;
  comparison_summary: string;
}

