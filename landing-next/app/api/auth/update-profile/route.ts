import { NextRequest, NextResponse } from 'next/server'
import jwt from 'jsonwebtoken'

const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key'
const AUTH_SERVICE_URL = process.env.AUTH_SERVICE_URL || 'http://localhost:8000'

export async function PUT(request: NextRequest) {
  try {
    // Get authorization header
    const authHeader = request.headers.get('authorization')
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return NextResponse.json({ detail: 'No token provided' }, { status: 401 })
    }

    const token = authHeader.substring(7)
    
    // Verify token
    let decoded
    try {
      decoded = jwt.verify(token, JWT_SECRET) as any
    } catch (error) {
      return NextResponse.json({ detail: 'Invalid token' }, { status: 401 })
    }

    // Get request body
    const body = await request.json()
    const { first_name, last_name, username, email, company_name, team_size } = body

    // Update user profile via auth service
    const response = await fetch(`${AUTH_SERVICE_URL}/users/${decoded.sub}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        first_name,
        last_name,
        username,
        email,
        company_name,
        team_size
      })
    })

    if (!response.ok) {
      const error = await response.json()
      return NextResponse.json({ detail: error.detail || 'Failed to update profile' }, { status: response.status })
    }

    const updatedUser = await response.json()
    return NextResponse.json(updatedUser)

  } catch (error) {
    console.error('Profile update error:', error)
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 })
  }
}
