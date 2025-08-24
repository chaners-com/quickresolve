import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const ownerId = searchParams.get('owner_id')

    if (!ownerId) {
      return NextResponse.json({ detail: 'owner_id parameter required' }, { status: 400 })
    }

    const response = await fetch(`${process.env.INGESTION_SERVICE_URL || 'http://localhost:8000'}/workspaces/?owner_id=${ownerId}`)
    
    if (!response.ok) {
      return NextResponse.json({ detail: 'Failed to fetch workspaces' }, { status: response.status })
    }

    const workspaces = await response.json()
    return NextResponse.json(workspaces)

  } catch (error) {
    console.error('Workspaces fetch error:', error)
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { name, owner_id, description } = body

    const response = await fetch(`${process.env.INGESTION_SERVICE_URL || 'http://localhost:8000'}/workspaces/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        name,
        owner_id,
        description
      })
    })

    if (!response.ok) {
      const error = await response.json()
      return NextResponse.json({ detail: error.detail || 'Failed to create workspace' }, { status: response.status })
    }

    const workspace = await response.json()
    return NextResponse.json(workspace)

  } catch (error) {
    console.error('Workspace creation error:', error)
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 })
  }
}