import { apiClient } from '../client'
import type { HealthResponse } from '../types'

export const healthApi = {
  check(): Promise<HealthResponse> {
    return apiClient.get<HealthResponse>('/health')
  },
}
