'use client'

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { signOut } from 'firebase/auth'
import { auth } from '../lib/firebase'

interface User {
  user_id: string
  email: string
  username: string
}

interface AuthContextType {
  user: User | null
  sessionToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (sessionToken: string, user: User) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null)
  const [sessionToken, setSessionToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const isAuthenticated = !!user && !!sessionToken

  const login = (newSessionToken: string, newUser: User) => {
    setSessionToken(newSessionToken)
    setUser(newUser)
    localStorage.setItem('session_token', newSessionToken)
    localStorage.setItem('user', JSON.stringify(newUser))
  }

  const logout = async () => {
    try {
      await signOut(auth)
      if (sessionToken) {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        await fetch(`${apiUrl}/api/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${sessionToken}`,
          },
        })
      }
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      setUser(null)
      setSessionToken(null)
      localStorage.removeItem('session_token')
      localStorage.removeItem('user')
    }
  }

  const checkAuth = async () => {
    setIsLoading(true)
    try {
      const storedToken = localStorage.getItem('session_token')
      const storedUser = localStorage.getItem('user')

      if (!storedToken || !storedUser) {
        setIsLoading(false)
        return
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${storedToken}`,
        },
      })

      if (response.ok) {
        const userData = await response.json()
        setSessionToken(storedToken)
        setUser({
          user_id: userData.user_id,
          email: userData.email,
          username: userData.username,
        })
      } else {
        localStorage.removeItem('session_token')
        localStorage.removeItem('user')
      }
    } catch (error) {
      console.error('Auth check error:', error)
      localStorage.removeItem('session_token')
      localStorage.removeItem('user')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    checkAuth()
  }, [])

  const value: AuthContextType = {
    user,
    sessionToken,
    isAuthenticated,
    isLoading,
    login,
    logout,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}