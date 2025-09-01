'use client'

import { useState, useEffect, ReactNode, createContext, useContext } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { User, AuthContextType } from '../../types/auth'

const AuthContext = createContext<AuthContextType | null>(null)

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within SecureAuthGuard')
  }
  return context
}

interface SecureAuthGuardProps {
  children: ReactNode
  fallback?: ReactNode
}

export default function SecureAuthGuard({ children, fallback }: SecureAuthGuardProps) {
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
      // Call the /me endpoint which uses secure HTTP-only cookies
      const response = await fetch('/api/auth/me', {
        method: 'GET',
        credentials: 'include', // Important: include cookies
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (response.ok) {
        const userData = await response.json()
        
        // Validate user data
        if (!userData.id || !userData.email || !userData.is_active) {
          console.error('Invalid user data received', userData)
          throw new Error('Invalid user data')
        }

        setUser(userData)
        setIsAuthenticated(true)
        
      } else if (response.status === 401) {
        // Unauthorized - redirect to login
        console.log('User not authenticated, redirecting to login')
        setUser(null)
        setIsAuthenticated(false)
        router.push('/login')
        return
      } else {
        throw new Error(`Authentication check failed: ${response.status}`)
      }
    } catch (error) {
      console.error('Authentication check failed:', error)
      setUser(null)
      setIsAuthenticated(false)
      
      // Only redirect on client-side errors if we're sure it's not a temporary network issue
      if (error instanceof TypeError && error.message.includes('fetch')) {
        console.error('Network error during auth check - user may be offline')
        // Don't redirect immediately on network errors - could be temporary
      } else {
        router.push('/login')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const logout = async () => {
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      })
    } catch (error) {
      console.error('Logout request failed:', error)
    } finally {
      // Always clear local state and redirect, even if the request fails
      setUser(null)
      setIsAuthenticated(false)
      router.push('/login')
    }
  }

  const refreshUser = async () => {
    await checkAuthentication()
  }

  const contextValue: AuthContextType = {
    user,
    isLoading,
    isAuthenticated,
    logout,
    refreshUser
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
    return (
      <AuthContext.Provider value={contextValue}>
        {children}
      </AuthContext.Provider>
    )
  }

  // If not authenticated, return null (user will be redirected)
  return null
}

// Export the user data hook for backward compatibility
export { type User }