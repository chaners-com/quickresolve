import { NextRequest, NextResponse } from 'next/server'

// Python backend URL
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8003'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { email, password, firstName, lastName, username, companyName, teamSize } = body

    // Validate input
    if (!email || !password || !firstName || !lastName) {
      return NextResponse.json(
        { error: 'Email, password, first name, and last name are required' },
        { status: 400 }
      )
    }

    // Validate password strength
    if (password.length < 8) {
      return NextResponse.json(
        { error: 'Password must be at least 8 characters long' },
        { status: 400 }
      )
    }

    // Forward request to Python backend
    const response = await fetch(`${BACKEND_URL}/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        email, 
        password, 
        first_name: firstName, 
        last_name: lastName,
        username: username || undefined,
        company_name: companyName || undefined,
        team_size: teamSize || undefined
      }),
    })

    const data = await response.json()

    if (response.ok) {
      // Return successful registration response
      return NextResponse.json({
        message: 'Registration successful',
        token: data.token,
        user: data.user
      })
    } else {
      // Return error from backend
      return NextResponse.json(
        { error: data.detail || 'Registration failed' },
        { status: response.status }
      )
    }

  } catch (error) {
    console.error('Registration API error:', error)
    
    // Check if it's a network error
    if (error instanceof TypeError && error.message.includes('fetch')) {
      return NextResponse.json(
        { error: 'Backend service unavailable' },
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