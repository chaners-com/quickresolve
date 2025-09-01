import { NextRequest, NextResponse } from 'next/server'
import { requireAuth } from '../../../../lib/auth'
import { createSecureResponse } from '../../../../lib/security'

export async function GET(request: NextRequest) {
  try {
    // Use secure session-based authentication
    const userOrResponse = await requireAuth(request)
    
    if (userOrResponse instanceof Response) {
      return userOrResponse
    }

    // Return user data
    return createSecureResponse({
      id: userOrResponse.id,
      email: userOrResponse.email,
      first_name: userOrResponse.first_name,
      last_name: userOrResponse.last_name,
      username: userOrResponse.username,
      is_active: userOrResponse.is_active,
      created_at: userOrResponse.created_at
    })

  } catch (error) {
    console.error('Auth verification error:', error)
    return createSecureResponse(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function POST() {
  return createSecureResponse(
    { error: 'Method not allowed' },
    { status: 405 }
  )
}