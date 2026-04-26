import { createContext, useContext, useEffect, useState } from 'react'
import { authAPI } from '../api/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const refreshUser = async () => {
    try {
      const res = await authAPI.me()
      setUser(res.data)
      return res.data
    } catch {
      setUser(null)
      return null
    }
  }

  useEffect(() => {
    refreshUser().finally(() => setLoading(false))
  }, [])

  const login = async (username, password) => {
    const res = await authAPI.login({ username, password })
    await refreshUser()
    return res.data
  }

  const logout = async () => {
    try {
      await authAPI.logout()
    } catch {
      // Ignore logout API errors and force local logout.
    }
    setUser(null)
    window.location.href = '/login'
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refreshUser, setUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
