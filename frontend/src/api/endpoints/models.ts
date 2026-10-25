import { apiClient } from '../client'
import type { ModelEvaluationResponse } from '../types'

export const modelsApi = {
  getEvaluation(): Promise<ModelEvaluationResponse> {
    return apiClient.get<ModelEvaluationResponse>('/api/v1/models/evaluation')
  },
}
