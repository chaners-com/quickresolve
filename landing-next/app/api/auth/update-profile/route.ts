import { NextRequest, NextResponse } from 'next/server'
import { requireAuth, getAuthToken } from '../../../../lib/auth'
import { createSecureResponse, createValidationErrorResponse, logSecurityEvent } from '../../../../lib/security'
import { sanitizeUserRegistrationData, detectSuspiciousPatterns } from '../../../../lib/sanitization'

const AUTH_SERVICE_URL = process.env.AUTH_SERVICE_URL || 'http://localhost:8003'

export async function PUT(request: NextRequest) {
  try {
    // Use secure session-based authentication
    const userOrResponse = await requireAuth(request)
    
    if (userOrResponse instanceof Response) {
      return userOrResponse // Return the error response
    }

    // Get and validate request body
    const body = await request.json()
    const { first_name, last_name, email, company_name, team_size } = body

    // Validate required fields
    if (!first_name || !last_name || !email) {
      return createValidationErrorResponse('first_name, last_name, and email are required')
    }

    // Sanitize and validate input data
    let sanitizedData
    try {
      sanitizedData = sanitizeUserRegistrationData({
        firstName: first_name,
        lastName: last_name,
        email,
        companyName: company_name,
        teamSize: team_size
      })
      
      // Check for suspicious patterns
      const allTextInputs = [
        first_name,
        last_name,
        email,
        company_name
      ].filter(Boolean).join(' ')
      
      const suspiciousPatterns = detectSuspiciousPatterns(allTextInputs)
      if (suspiciousPatterns.length > 0) {
        logSecurityEvent('SUSPICIOUS_PROFILE_UPDATE', { 
          userId: userOrResponse.id,
          patterns: suspiciousPatterns 
        }, request)
        return createValidationErrorResponse('Invalid input detected')
      }
    } catch (error) {
      return createValidationErrorResponse(error instanceof Error ? error.message : 'Invalid input')
    }

    // Get auth token for backend API call
    const authToken = await getAuthToken()
    if (!authToken) {
      return createValidationErrorResponse('Authentication token not found')
    }

    // Update user profile via auth service
    const response = await fetch(`${AUTH_SERVICE_URL}/users/${userOrResponse.id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`,
      },
      body: JSON.stringify({
        first_name: sanitizedData.firstName,
        last_name: sanitizedData.lastName,
        email: sanitizedData.email,
        company_name: sanitizedData.companyName,
        team_size: sanitizedData.teamSize
      })
    })

    const data = await response.json().catch(() => ({}))

    if (!response.ok) {
      return createSecureResponse(
        { detail: data.detail || 'Failed to update profile' }, 
        { status: response.status }
      )
    }

    logSecurityEvent('PROFILE_UPDATED', { 
      userId: userOrResponse.id,
      updatedFields: Object.keys(sanitizedData).filter(key => sanitizedData[key as keyof typeof sanitizedData] !== undefined)
    }, request)

    return createSecureResponse(data)

  } catch (error) {
    console.error('Profile update error:', error)
    return createSecureResponse({ detail: 'Internal server error' }, { status: 500 })
  }
}
