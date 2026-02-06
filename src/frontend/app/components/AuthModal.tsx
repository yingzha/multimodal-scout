'use client'

import { useState } from 'react'
import { GoogleAuthProvider, signInWithPopup } from 'firebase/auth'
import { auth } from '../lib/firebase'

interface AuthModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: (sessionToken: string, userInfo: { user_id: string; email: string; username: string }) => void
  asPage?: boolean
}

export default function AuthModal({ isOpen, onClose, onSuccess, asPage = false }: AuthModalProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const handleGoogleSignIn = async () => {
    setIsLoading(true)
    setError('')

    try {
      const provider = new GoogleAuthProvider()
      const result = await signInWithPopup(auth, provider)
      const idToken = await result.user.getIdToken()

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/auth/google`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: idToken }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Authentication failed')
      }

      if (data.success) {
        const meResponse = await fetch(`${apiUrl}/api/auth/me`, {
          headers: { 'Authorization': `Bearer ${data.session_token}` },
        })
        const userInfo = await meResponse.json()

        onSuccess(data.session_token, {
          user_id: userInfo.user_id,
          email: userInfo.email,
          username: userInfo.username,
        })
        onClose()
      }
    } catch (error: any) {
      if (error.code === 'auth/popup-closed-by-user') {
        return
      }
      setError(error.message || 'Sign in failed')
    } finally {
      setIsLoading(false)
    }
  }

  if (!isOpen) return null

  const contentDiv = (
    <div className={`${asPage ? 'w-full' : 'bg-white rounded-lg p-8 max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto'}`}>
      <div className="flex justify-center items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">
          Sign In
        </h2>
      </div>

      {error && (
        <div className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
          {error}
        </div>
      )}

      <button
        onClick={handleGoogleSignIn}
        disabled={isLoading}
        className={`w-full py-3 px-4 rounded-lg font-medium transition-colors ${
          isLoading
            ? 'bg-gray-500 cursor-not-allowed'
            : 'bg-gray-500 hover:bg-gray-600'
        } text-white flex items-center justify-center gap-3`}
      >
        {isLoading ? (
          <div className="flex items-center justify-center">
            <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-2"></div>
            Signing in...
          </div>
        ) : (
          <>
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            Sign in with Google
          </>
        )}
      </button>

      <div className="mt-4 text-xs text-gray-700 text-center">
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
