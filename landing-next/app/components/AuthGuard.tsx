'use client'

import { useState, useEffect, ReactNode } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { fetchWithRetry, isServiceUnavailableError } from '../../utils/apiUtils'

interface User {
  id: number
  email: string
  username?: string
  first_name?: string
  last_name?: string
  is_active: boolean
  created_at: string
}

interface AuthGuardProps {
  children: ReactNode
  fallback?: ReactNode
}

export default function AuthGuard({ children, fallback }: AuthGuardProps) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    checkAuthentication()
  }, [pathname])

  const checkAuthentication = async () => {
    try {
      const response = await fetchWithRetry('/api/auth/me', {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        }
      }, 2, 1000) // 2 retries with 1 second delay

      if (response.ok) {
        const userData = await response.json()
        
        // Additional security checks
        if (!userData.id || !userData.email || typeof userData.is_active !== 'boolean') {
          console.error('Invalid user data received', userData)
          throw new Error('Invalid user data')
        }

        setUser(userData)
        setIsAuthenticated(true)
        
      } else if (response.status === 401 || response.status === 403) {
        // Session is invalid/expired
        console.log('Session invalid/expired, redirecting to login')
        redirectToLogin()
        return
      } else {
        throw new Error(`Auth check failed: ${response.status}`)
      }
    } catch (error) {
      console.error('Authentication check failed:', error)
      
      if (isServiceUnavailableError(error)) {
        // Service temporarily unavailable - redirect to login for security
        console.error('Auth service unavailable, redirecting to login for security')
        redirectToLogin()
      } else {
        // Other errors - redirect to login
        redirectToLogin()
      }
    } finally {
      setIsLoading(false)
    }
  }

  const redirectToLogin = () => {
    // Clear any cached data
    if (typeof window !== 'undefined') {
      localStorage.removeItem('authToken') // Clean up old token storage
      localStorage.removeItem('user') // Clean up old user data
    }
    router.push('/login')
  }

  // Show loading spinner while checking authentication
  if (isLoading) {
    return (
      fallback || (
        <div className="flex items-center justify-center min-h-screen bg-gray-900">
          <div className="flex items-center space-x-2 text-white">
            <div className="w-8 h-8 border-2 border-white/30 border-t-emerald-500 rounded-full animate-spin"></div>
            <span>Verifying authentication...</span>
          </div>
        </div>
      )
    )
  }

  // Only render children if authenticated
  if (isAuthenticated && user) {
    return <>{children}</>
  }

  // If not authenticated, return null (user will be redirected)
  return null
}

// Export the user data hook for use in components
export { type User }