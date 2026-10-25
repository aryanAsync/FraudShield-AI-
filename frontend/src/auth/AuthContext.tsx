import React, { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { authApi, getAuthToken, onUnauthorized, setAuthToken } from '../api'
import type { LoginRequest, UserResponse, UserRole } from '../api/types'

interface AuthContextType {
  user: UserResponse | null
  isLoading: boolean
  isAuthenticated: boolean
  role: UserRole | null
  login: (credentials: LoginRequest) => Promise<void>
  logout: () => Promise<void>
  refreshProfile: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserResponse | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)

  const clearSession = useCallback(() => {
    setAuthToken(null)
    setUser(null)
  }, [])

  const loadUserProfile = useCallback(async () => {
    const token = getAuthToken()
    if (!token) {
      setUser(null)
      setIsLoading(false)
      return
    }

    try {
      const profile = await authApi.getMe()
      setUser(profile)
    } catch {
      // If profile request fails (e.g. 401 token expired or deactivated)
      clearSession()
    } finally {
      setIsLoading(false)
    }
  }, [clearSession])

  useEffect(() => {
    void loadUserProfile()

    // Subscribe to global 401s
    const unsubscribe = onUnauthorized(() => {
      clearSession()
    })

    return () => {
      unsubscribe()
    }
  }, [loadUserProfile, clearSession])

  const login = async (credentials: LoginRequest): Promise<void> => {
    setIsLoading(true)
    try {
      const tokenResp = await authApi.login(credentials)
      setAuthToken(tokenResp.access_token)
      // Immediately fetch current authenticated profile from server
      const profile = await authApi.getMe()
      setUser(profile)
    } catch (err) {
      clearSession()
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  const logout = async (): Promise<void> => {
    setIsLoading(true)
    try {
      await authApi.logout()
    } catch {
      // Even if network failure, clear local session
    } finally {
      clearSession()
      setIsLoading(false)
    }
  }

  const refreshProfile = async (): Promise<void> => {
    if (!getAuthToken()) return
    try {
      const profile = await authApi.getMe()
      setUser(profile)
    } catch {
      clearSession()
    }
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        role: user?.role ?? null,
        login,
        logout,
        refreshProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
