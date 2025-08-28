'use client'

import { useState } from 'react'

interface AuthModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: (sessionToken: string, userInfo: { user_id: string; email: string; username: string }) => void
  asPage?: boolean
}

export default function AuthModal({ isOpen, onClose, onSuccess, asPage = false }: AuthModalProps) {
  const [isLogin, setIsLogin] = useState(true)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [username, setUsername] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const fetchUserInfo = async (sessionToken: string) => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const response = await fetch(`${apiUrl}/api/auth/me`, {
      headers: {
        'Authorization': `Bearer ${sessionToken}`,
      },
    })
    if (response.ok) {
      const userData = await response.json()
      return {
        user_id: userData.user_id,
        email: userData.email,
        username: userData.username,
      }
    }
    throw new Error('Failed to fetch user info')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const endpoint = isLogin ? '/api/auth/login' : '/api/auth/register'
      
      const response = await fetch(`${apiUrl}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(isLogin ? { email, password } : { email, password, username }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Authentication failed')
      }

      if (data.success) {
        // For login, we need to fetch user info to get username
        // For registration, username should be in the response
        const userInfo = isLogin 
          ? await fetchUserInfo(data.session_token)
          : { user_id: data.user_id, email, username }
        
        onSuccess(data.session_token, userInfo)
        resetForm()
        onClose()
      } else {
        setError(data.message || 'Authentication failed')
      }
    } catch (error: any) {
      setError(error.message || 'An error occurred')
    } finally {
      setIsLoading(false)
    }
  }

  const resetForm = () => {
    setEmail('')
    setPassword('')
    setUsername('')
    setError('')
    setIsLogin(true)
  }


  if (!isOpen) return null

  const contentDiv = (
    <div className={`${asPage ? 'w-full' : 'bg-white rounded-lg p-8 max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto'}`}>
        <div className="flex justify-center items-center mb-6">
          <h2 className="text-2xl font-bold text-gray-800">
            {isLogin ? 'Login' : 'Register'}
          </h2>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-gray-400 focus:border-gray-400"
              placeholder="Enter your email"
            />
          </div>

          {!isLogin && (
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
                Username
              </label>
              <input
                type="text"
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required={!isLogin}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-gray-400 focus:border-gray-400"
                placeholder="Enter your username"
              />
            </div>
          )}

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-gray-400 focus:border-gray-400"
              placeholder="Enter your password"
            />
          </div>

          {error && (
            <div className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg p-3">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className={`w-full py-3 px-4 rounded-lg font-medium transition-colors ${
              isLoading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-gray-500 hover:bg-gray-600'
            } text-white`}
          >
            {isLoading ? (
              <div className="flex items-center justify-center">
                <div className="animate-spin w-4 h-4 border-2 border-white  border-t-transparent rounded-full mr-2"></div>
                {isLogin ? 'Logging in...' : 'Creating account...'}
              </div>
            ) : (
              <>{isLogin ? 'Login' : 'Create Account'}</>
            )}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-sm text-gray-600">
            {isLogin ? "Don't have an account?" : 'Already have an account?'}
            <button
              type="button"
              onClick={() => {
                setIsLogin(!isLogin)
                setError('')
              }}
              className="ml-2 text-purple-500 bg-gray-400 hover:text-gray-800 font-medium"
            >
              {isLogin ? 'Sign up' : 'Login'}
            </button>
          </p>
        </div>

        <div className="mt-4 text-xs text-gray-500 text-center">
          <p>Your data is private and secure. Each user has their own bookmark collection.</p>
        </div>
      </div>
    )

  if (asPage) {
    return (
      <div className="bg-gray-50 rounded-lg p-6 shadow-sm border border-gray-200 max-w-md mx-auto">
        {contentDiv}
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      {contentDiv}
    </div>
  )
}