import { NextRequest, NextResponse } from 'next/server'
import { requireAuth, getAuthToken } from '../../../../lib/auth'
import { createSecureResponse, createValidationErrorResponse, logSecurityEvent } from '../../../../lib/security'

const AUTH_SERVICE_URL = process.env.AUTH_SERVICE_URL || 'http://localhost:8003'

export async function PUT(request: NextRequest) {
  try {
    // Use secure session-based authentication
    const userOrResponse = await requireAuth(request)
    
    if (userOrResponse instanceof Response) {
      return userOrResponse // Return the error response
    }

    const { current_password, new_password } = await request.json()

    // Validate input
    if (!current_password || !new_password) {
      return createValidationErrorResponse('current_password and new_password are required')
    }

    // Validate new password strength
    try {
      const passwordValidation = validatePassword(new_password)
      if (!passwordValidation.isValid) {
        return createValidationErrorResponse(passwordValidation.message)
      }
    } catch (error) {
      return createValidationErrorResponse('Invalid password format')
    }

    // Get auth token for backend API call
    const authToken = await getAuthToken()
    if (!authToken) {
      return createValidationErrorResponse('Authentication token not found')
    }

    // Call backend to change password
    const response = await fetch(
      `${AUTH_SERVICE_URL}/users/${userOrResponse.id}/change-password`,
      {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`,
        },
        body: JSON.stringify({ current_password, new_password }),
      }
    )

    const data = await response.json().catch(() => ({}))
    
    if (!response.ok) {
      if (response.status === 400 && data.detail?.includes('incorrect')) {
        logSecurityEvent('FAILED_PASSWORD_CHANGE', { 
          userId: userOrResponse.id,
          reason: 'incorrect_current_password'
        }, request)
      }
      
      return createSecureResponse(
        { detail: data.detail || 'Failed to change password' },
        { status: response.status }
      )
    }

    logSecurityEvent('PASSWORD_CHANGED', { 
      userId: userOrResponse.id 
    }, request)

    return createSecureResponse({ message: 'Password changed successfully' })
    
  } catch (error) {
    console.error('Password change error:', error)
    return createSecureResponse({ detail: 'Internal server error' }, { status: 500 })
  }
}

function validatePassword(password: string): { isValid: boolean, message: string } {
  if (password.length < 8) {
    return { isValid: false, message: 'Password must be at least 8 characters long' }
  }
  
  if (!/[A-Z]/.test(password)) {
    return { isValid: false, message: 'Password must contain at least one uppercase letter' }
  }
  
  if (!/[a-z]/.test(password)) {
    return { isValid: false, message: 'Password must contain at least one lowercase letter' }
  }
  
  if (!/\d/.test(password)) {
    return { isValid: false, message: 'Password must contain at least one number' }
  }
  
  return { isValid: true, message: 'Password is valid' }
}
