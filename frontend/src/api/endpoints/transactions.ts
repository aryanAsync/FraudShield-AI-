import { apiClient } from '../client'
import type {
  BatchScoreRequest,
  BatchScoreResponse,
  FeatureAttribution,
  PaginatedTransactionsResponse,
  PredictionHistoryResponse,
  RiskLevel,
  ScoreTransactionRequest,
  ScoreTransactionResponse,
  TransactionDetailResponse,
} from '../types'

export interface ListTransactionsParams {
  page?: number
  page_size?: number
  risk_level?: RiskLevel | string
  predicted_class?: number
  sort_by?: 'created_at' | 'amount' | 'transaction_time' | 'id'
  sort_order?: 'asc' | 'desc'
}

export const transactionsApi = {
  list(params?: ListTransactionsParams): Promise<PaginatedTransactionsResponse> {
    return apiClient.get<PaginatedTransactionsResponse>('/api/v1/transactions', {
      params: {
        page: params?.page ?? 1,
        page_size: params?.page_size ?? 20,
        risk_level: params?.risk_level || undefined,
        predicted_class:
          params?.predicted_class !== undefined && params?.predicted_class !== null
            ? params.predicted_class
            : undefined,
        sort_by: params?.sort_by ?? 'created_at',
        sort_order: params?.sort_order ?? 'desc',
      },
    })
  },

  getById(transactionId: number): Promise<TransactionDetailResponse> {
    return apiClient.get<TransactionDetailResponse>(`/api/v1/transactions/${transactionId}`)
  },

  getPredictions(transactionId: number): Promise<PredictionHistoryResponse> {
    return apiClient.get<PredictionHistoryResponse>(
      `/api/v1/transactions/${transactionId}/predictions`
    )
  },

  score(payload: ScoreTransactionRequest): Promise<ScoreTransactionResponse> {
    return apiClient.post<ScoreTransactionResponse>('/api/v1/transactions/score', payload)
  },

  batchScore(payload: BatchScoreRequest): Promise<BatchScoreResponse> {
    return apiClient.post<BatchScoreResponse>('/api/v1/transactions/batch-score', payload)
  },

  explain(transactionId: number, topK: number = 10): Promise<FeatureAttribution[]> {
    return apiClient.post<FeatureAttribution[]>(
      `/api/v1/transactions/${transactionId}/explain`,
      undefined,
      { params: { top_k: topK } }
    )
  },
}

