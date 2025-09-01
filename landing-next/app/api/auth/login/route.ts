import { NextRequest, NextResponse } from 'next/server'
import { setSessionCookies } from '../../../../lib/auth'
import { loginLimiter, getClientIP } from '../../../../lib/rateLimiter'
import { sanitizeEmail, detectSuspiciousPatterns } from '../../../../lib/sanitization'
import { createSecureResponse, createRateLimitResponse, createValidationErrorResponse, createServerErrorResponse, logSecurityEvent } from '../../../../lib/security'

// Auth service URL
const AUTH_SERVICE_URL = process.env.AUTH_SERVICE_URL || 'http://localhost:8003'

export async function POST(request: NextRequest) {
  try {
    // Enhanced rate limiting
    const clientIP = getClientIP(request)
    const rateLimitResult = await loginLimiter.checkLimit(clientIP)
    
    if (!rateLimitResult.success) {
      logSecurityEvent('RATE_LIMIT_EXCEEDED', { 
        endpoint: '/auth/login',
        clientIP,
        limit: rateLimitResult.limit 
      }, request)
      
      const retryAfterMs = rateLimitResult.reset.getTime() - Date.now()
      return createRateLimitResponse(retryAfterMs)
    }

    const body = await request.json()
    const { password } = body

    // Validate input
    if (!body.email || !password) {
      return createValidationErrorResponse('Email and password are required')
    }

    // Sanitize email and check for suspicious patterns
    let sanitizedEmail
    try {
      sanitizedEmail = sanitizeEmail(body.email)
      
      const suspiciousPatterns = detectSuspiciousPatterns(body.email + ' ' + password)
      if (suspiciousPatterns.length > 0) {
        logSecurityEvent('SUSPICIOUS_LOGIN_ATTEMPT', { 
          patterns: suspiciousPatterns,
          email: body.email.substring(0, 3) + '***' // Log partial email only
        }, request)
        return createValidationErrorResponse('Invalid input detected')
      }
    } catch (error) {
      return createValidationErrorResponse('Invalid email format')
    }

    // Additional password validation
    if (password.length < 8) {
      return createValidationErrorResponse('Invalid password format')
    }

    // Forward request to Python backend
    const response = await fetch(`${AUTH_SERVICE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email: sanitizedEmail, password }),
    })

    const data = await response.json()

    if (response.ok) {
      // Validate user data from backend
      if (!data.user || !data.user.id || !data.user.email) {
        logSecurityEvent('INVALID_USER_DATA', { 
          receivedData: data.user ? 'partial' : 'none' 
        }, request)
        return createServerErrorResponse()
      }

      // Set secure HTTP-only cookies
      await setSessionCookies(data.user, data.token)

      // Return success without sensitive data
      return createSecureResponse({
        message: 'Login successful',
        user: {
          id: data.user.id,
          email: data.user.email,
          first_name: data.user.first_name,
          last_name: data.user.last_name,
          username: data.user.username,
          company_name: data.user.company_name,
          team_size: data.user.team_size,
          is_active: data.user.is_active
        }
      })
    } else {
      // Log failed login attempts
      if (response.status === 401) {
        logSecurityEvent('FAILED_LOGIN_ATTEMPT', { 
          email: sanitizedEmail.substring(0, 3) + '***',
          status: response.status
        }, request)
      }
      
      // Return error from backend
      return createSecureResponse(
        { error: data.error || data.detail || 'Login failed' },
        { status: response.status }
      )
    }

  } catch (error) {
    logSecurityEvent('LOGIN_API_ERROR', { 
      error: error instanceof Error ? error.message : 'Unknown error'
    }, request)
    
    // Check if it's a network error
    if (error instanceof TypeError && error.message.includes('fetch')) {
      return createSecureResponse(
        { error: 'Auth service is temporarily unavailable. Please try again in a moment.' },
        { status: 503 }
      )
    }

    return createServerErrorResponse()
  }
}

export async function GET() {
  return createSecureResponse(
    { error: 'Method not allowed' },
    { status: 405 }
  )
}