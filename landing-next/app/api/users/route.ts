import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const username = searchParams.get('username')

    if (!username) {
      return NextResponse.json({ detail: 'username parameter required' }, { status: 400 })
    }

    const response = await fetch(`${process.env.INGESTION_SERVICE_URL || 'http://localhost:8000'}/users/?username=${encodeURIComponent(username)}`)
    
    if (!response.ok) {
      return NextResponse.json({ detail: 'Failed to fetch users' }, { status: response.status })
    }

    const users = await response.json()
    return NextResponse.json(users)

  } catch (error) {
    console.error('Users fetch error:', error)
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { username } = body

    if (!username) {
      return NextResponse.json({ detail: 'username is required' }, { status: 400 })
    }

    const response = await fetch(`${process.env.INGESTION_SERVICE_URL || 'http://localhost:8000'}/users/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username })
    })

    if (!response.ok) {
      const error = await response.json()
      return NextResponse.json({ detail: error.detail || 'Failed to create user' }, { status: response.status })
    }

    const user = await response.json()
    return NextResponse.json(user)

  } catch (error) {
    console.error('User creation error:', error)
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 })
  }
}