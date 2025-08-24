import { NextRequest, NextResponse } from 'next/server'
import jwt, { JwtPayload } from 'jsonwebtoken'

const AUTH_SERVICE_URL = process.env.BACKEND_URL || 'http://localhost:8000'
const JWT_SECRET = process.env.JWT_SECRET 

export async function PUT(request: NextRequest) {
  try {
    const authHeader = request.headers.get('authorization')
    if (!authHeader?.startsWith('Bearer ')) {
      return NextResponse.json({ detail: 'No token provided' }, { status: 401 })
    }

    const token = authHeader.slice(7)

    if (!JWT_SECRET) {
      return NextResponse.json(
        { detail: 'Server misconfigured: JWT_SECRET is not set' },
        { status: 500 }
      )
    }

    let decoded: JwtPayload
    try {
      decoded = jwt.verify(token, JWT_SECRET) as JwtPayload
    } catch {
      return NextResponse.json({ detail: 'Invalid token' }, { status: 401 })
    }

    const { current_password, new_password } = await request.json()

    if (!current_password || !new_password) {
      return NextResponse.json(
        { detail: 'current_password and new_password are required' },
        { status: 400 }
      )
    }

    // If the backend expects the user id:
    const userId = decoded.sub
    const response = await fetch(
      `${AUTH_SERVICE_URL}/users/${userId}/change-password`,
      {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          // forward the bearer so backend can also auth it if needed
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ current_password, new_password }),
      }
    )

    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      return NextResponse.json(
        { detail: data.detail || 'Failed to change password' },
        { status: response.status }
      )
    }

    return NextResponse.json({ message: 'Password changed successfully' })
  } catch (error) {
    console.error('Password change error:', error)
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 })
  }
}
