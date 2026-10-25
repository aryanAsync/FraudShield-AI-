import { apiClient, setAuthToken } from '../client'
import type { LoginRequest, TokenResponse, UserResponse } from '../types'

export const authApi = {
  async login(credentials: LoginRequest): Promise<TokenResponse> {
    const data = await apiClient.post<TokenResponse>('/api/v1/auth/login', credentials)
    if (data.access_token) {
      setAuthToken(data.access_token)
    }
    return data
  },

  async getMe(): Promise<UserResponse> {
    return apiClient.get<UserResponse>('/api/v1/auth/me')
  },

  async logout(): Promise<{ message: string }> {
    try {
      return await apiClient.post<{ message: string }>('/api/v1/auth/logout')
    } finally {
      setAuthToken(null)
    }
  },
}
