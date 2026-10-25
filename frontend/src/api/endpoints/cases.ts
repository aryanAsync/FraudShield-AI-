import { apiClient } from '../client'
import type {
  CaseCreateRequest,
  CaseDetailResponse,
  CaseNoteCreateRequest,
  CaseNoteResponse,
  CaseResponse,
  CaseUpdateRequest,
  PaginatedCaseNotesResponse,
  PaginatedCasesResponse,
} from '../types'

export interface ListCasesParams {
  page?: number
  page_size?: number
  status?: string
  assigned_user_id?: number
  transaction_id?: number
  risk_level?: string
  predicted_class?: number
  created_from?: string | null
  created_to?: string | null
}

export const casesApi = {
  list(params?: ListCasesParams): Promise<PaginatedCasesResponse> {
    return apiClient.get<PaginatedCasesResponse>('/api/v1/cases', {
      params: {
        page: params?.page ?? 1,
        page_size: params?.page_size ?? 20,
        status: params?.status || undefined,
        assigned_user_id: params?.assigned_user_id || undefined,
        transaction_id: params?.transaction_id || undefined,
        risk_level: params?.risk_level || undefined,
        predicted_class:
          params?.predicted_class !== undefined && params?.predicted_class !== null
            ? params.predicted_class
            : undefined,
        created_from: params?.created_from || undefined,
        created_to: params?.created_to || undefined,
      },
    })
  },

  getById(caseId: number): Promise<CaseDetailResponse> {
    return apiClient.get<CaseDetailResponse>(`/api/v1/cases/${caseId}`)
  },

  create(payload: CaseCreateRequest): Promise<CaseResponse> {
    return apiClient.post<CaseResponse>('/api/v1/cases', payload)
  },

  update(caseId: number, payload: CaseUpdateRequest): Promise<CaseResponse> {
    return apiClient.patch<CaseResponse>(`/api/v1/cases/${caseId}`, payload)
  },

  listNotes(
    caseId: number,
    page: number = 1,
    page_size: number = 100
  ): Promise<PaginatedCaseNotesResponse> {
    return apiClient.get<PaginatedCaseNotesResponse>(`/api/v1/cases/${caseId}/notes`, {
      params: { page, page_size },
    })
  },

  addNote(caseId: number, payload: CaseNoteCreateRequest): Promise<CaseNoteResponse> {
    return apiClient.post<CaseNoteResponse>(`/api/v1/cases/${caseId}/notes`, payload)
  },
}
