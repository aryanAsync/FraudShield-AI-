import { apiClient } from '../client'
import type {
  PaginatedUsersResponse,
  UserCreateRequest,
  UserResponse,
  UserRole,
  UserUpdateRequest,
} from '../types'

export interface ListUsersParams {
  page?: number
  page_size?: number
  role?: UserRole
  is_active?: boolean
}

export const usersApi = {
  list(params?: ListUsersParams): Promise<PaginatedUsersResponse> {
    return apiClient.get<PaginatedUsersResponse>('/api/v1/users', {
      params: {
        page: params?.page ?? 1,
        page_size: params?.page_size ?? 20,
        role: params?.role || undefined,
        is_active:
          params?.is_active !== undefined && params?.is_active !== null
            ? params.is_active
            : undefined,
      },
    })
  },

  getById(userId: number): Promise<UserResponse> {
    return apiClient.get<UserResponse>(`/api/v1/users/${userId}`)
  },

  create(payload: UserCreateRequest): Promise<UserResponse> {
    return apiClient.post<UserResponse>('/api/v1/users', payload)
  },

  update(userId: number, payload: UserUpdateRequest): Promise<UserResponse> {
    return apiClient.patch<UserResponse>(`/api/v1/users/${userId}`, payload)
  },
}
