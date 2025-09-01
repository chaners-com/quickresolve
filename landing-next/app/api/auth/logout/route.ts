import { NextRequest, NextResponse } from 'next/server'
import { clearSession } from '../../../../lib/auth'
import { createSecureResponse } from '../../../../lib/security'

export async function POST(request: NextRequest) {
  try {
    // Clear the session cookies
    clearSession()

    return createSecureResponse({
      message: 'Logged out successfully'
    })

  } catch (error) {
    console.error('Logout error:', error)
    return createSecureResponse(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function GET() {
  return createSecureResponse(
    { error: 'Method not allowed' },
    { status: 405 }
  )
}