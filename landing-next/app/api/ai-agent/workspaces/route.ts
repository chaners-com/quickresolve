import { NextResponse } from 'next/server'

export async function GET() {
  try {
    const response = await fetch(`${process.env.AI_AGENT_SERVICE_URL || 'http://localhost:8001'}/workspaces`)
    
    if (!response.ok) {
      return NextResponse.json({ detail: 'Failed to fetch workspaces' }, { status: response.status })
    }

    const workspaces = await response.json()
    return NextResponse.json(workspaces)

  } catch (error) {
    console.error('AI workspaces fetch error:', error)
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 })
  }
}
