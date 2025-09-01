import { NextRequest, NextResponse } from 'next/server'
import { setSessionCookies } from '../../../../lib/auth'
import { signupLimiter, getClientIP } from '../../../../lib/rateLimiter'
import { sanitizeUserRegistrationData, detectSuspiciousPatterns } from '../../../../lib/sanitization'

// Auth service URL
const AUTH_SERVICE_URL = process.env.AUTH_SERVICE_URL || 'http://localhost:8003'

// Password validation function
interface PasswordValidation {
  isValid: boolean
  message: string
}

function validatePassword(password: string): PasswordValidation {
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

export async function POST(request: NextRequest) {
  try {
    // Enhanced rate limiting
    const clientIP = getClientIP(request)
    const rateLimitResult = await signupLimiter.checkLimit(clientIP)
    
    if (!rateLimitResult.success) {
      return NextResponse.json(
        { 
          error: 'Too many signup attempts. Please try again later.',
          retryAfter: rateLimitResult.reset 
        },
        { 
          status: 429,
          headers: {
            'X-RateLimit-Limit': rateLimitResult.limit.toString(),
            'X-RateLimit-Remaining': rateLimitResult.remaining.toString(),
            'X-RateLimit-Reset': rateLimitResult.reset.getTime().toString(),
            'Retry-After': Math.ceil((rateLimitResult.reset.getTime() - Date.now()) / 1000).toString()
          }
        }
      )
    }

    const body = await request.json()
    const { password } = body

    // Basic input validation
    if (!body.email || !password || !body.firstName || !body.lastName) {
      return NextResponse.json(
        { error: 'Email, password, first name, and last name are required' },
        { status: 400 }
      )
    }

    // Sanitize and validate input data
    let sanitizedData
    try {
      sanitizedData = sanitizeUserRegistrationData(body)
      
      // Check for suspicious patterns in all text fields
      const allTextInputs = [
        body.email,
        body.firstName,
        body.lastName,
        body.username,
        body.companyName
      ].filter(Boolean).join(' ')
      
      const suspiciousPatterns = detectSuspiciousPatterns(allTextInputs)
      if (suspiciousPatterns.length > 0) {
        console.warn(`Suspicious signup attempt from ${getClientIP(request)}:`, suspiciousPatterns)
        return NextResponse.json(
          { error: 'Invalid input detected' },
          { status: 400 }
        )
      }
    } catch (error) {
      return NextResponse.json(
        { error: error instanceof Error ? error.message : 'Invalid input' },
        { status: 400 }
      )
    }

    // Comprehensive password validation (matching backend requirements)
    const passwordValidation = validatePassword(password)
    if (!passwordValidation.isValid) {
      return NextResponse.json(
        { error: passwordValidation.message },
        { status: 400 }
      )
    }

    // Forward sanitized data to Python backend
    const response = await fetch(`${AUTH_SERVICE_URL}/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        email: sanitizedData.email,
        password, 
        first_name: sanitizedData.firstName, 
        last_name: sanitizedData.lastName,
        username: sanitizedData.username || undefined,
        company_name: sanitizedData.companyName || undefined,
        team_size: sanitizedData.teamSize || undefined
      }),
    })

    const data = await response.json()

    if (response.ok) {
      // Validate user data from backend
      if (!data.user || !data.user.id || !data.user.email) {
        return NextResponse.json(
          { error: 'Invalid user data received from server' },
          { status: 500 }
        )
      }

      // Set secure HTTP-only cookies
      await setSessionCookies(data.user, data.token)

      // Return success without sensitive data
      return NextResponse.json({
        message: 'Registration successful',
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
      // Return error from backend
      return NextResponse.json(
        { error: data.detail || data.error || 'Registration failed' },
        { status: response.status }
      )
    }

  } catch (error) {
    console.error('Registration API error:', error)
    
    if (error instanceof TypeError && error.message.includes('fetch')) {
      return NextResponse.json(
        { error: 'Auth service is temporarily unavailable. Please try again in a moment.' },
        { status: 503 }
      )
    }

    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function GET() {
  return NextResponse.json(
    { error: 'Method not allowed' },
    { status: 405 }
  )
}