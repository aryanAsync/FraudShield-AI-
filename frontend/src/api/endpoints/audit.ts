import { apiClient } from '../client'
import type { PaginatedAuditLogsResponse } from '../types'

export interface ListAuditLogsParams {
  page?: number
  page_size?: number
  actor_id?: string
  action?: string
  entity_type?: string
  entity_id?: string
  created_from?: string | null
  created_to?: string | null
}

export const auditApi = {
  list(params?: ListAuditLogsParams): Promise<PaginatedAuditLogsResponse> {
    return apiClient.get<PaginatedAuditLogsResponse>('/api/v1/audit-logs', {
      params: {
        page: params?.page ?? 1,
        page_size: params?.page_size ?? 20,
        actor_id: params?.actor_id || undefined,
        action: params?.action || undefined,
        entity_type: params?.entity_type || undefined,
        entity_id: params?.entity_id || undefined,
        created_from: params?.created_from || undefined,
        created_to: params?.created_to || undefined,
      },
    })
  },
}
