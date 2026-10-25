import { apiClient } from '../client'
import type {
  AnalyticsOverviewResponse,
  AnalyticsTrendsResponse,
  CaseStatusDistributionResponse,
  FeatureImportanceResponse,
  RiskDistributionResponse,
  RiskLevel,
} from '../types'

export interface AnalyticsDateFilter {
  start_date?: string | null
  end_date?: string | null
}

export const analyticsApi = {
  getOverview(filters?: AnalyticsDateFilter): Promise<AnalyticsOverviewResponse> {
    return apiClient.get<AnalyticsOverviewResponse>('/api/v1/analytics/overview', {
      params: {
        start_date: filters?.start_date,
        end_date: filters?.end_date,
      },
    })
  },

  getRiskDistribution(filters?: AnalyticsDateFilter): Promise<RiskDistributionResponse> {
    return apiClient.get<RiskDistributionResponse>('/api/v1/analytics/risk-distribution', {
      params: {
        start_date: filters?.start_date,
        end_date: filters?.end_date,
      },
    })
  },

  getTrends(
    interval: 'hour' | 'day' = 'day',
    filters?: AnalyticsDateFilter
  ): Promise<AnalyticsTrendsResponse> {
    return apiClient.get<AnalyticsTrendsResponse>('/api/v1/analytics/trends', {
      params: {
        interval,
        start_date: filters?.start_date,
        end_date: filters?.end_date,
      },
    })
  },

  getCaseStatusDistribution(
    filters?: AnalyticsDateFilter
  ): Promise<CaseStatusDistributionResponse> {
    return apiClient.get<CaseStatusDistributionResponse>(
      '/api/v1/analytics/case-status-distribution',
      {
        params: {
          start_date: filters?.start_date,
          end_date: filters?.end_date,
        },
      }
    )
  },

  getFeatureImportance(params?: {
    risk_level?: RiskLevel | string
    limit?: number
    start_date?: string | null
    end_date?: string | null
  }): Promise<FeatureImportanceResponse> {
    return apiClient.get<FeatureImportanceResponse>('/api/v1/analytics/feature-importance', {
      params: {
        risk_level: params?.risk_level ?? 'HIGH',
        limit: params?.limit ?? 10,
        start_date: params?.start_date,
        end_date: params?.end_date,
      },
    })
  },
}
