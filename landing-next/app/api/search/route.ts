import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const query = searchParams.get('query')
    const workspaceId = searchParams.get('workspace_id')

    if (!query) {
      return NextResponse.json({ detail: 'query parameter required' }, { status: 400 })
    }

    if (!workspaceId) {
      return NextResponse.json({ detail: 'workspace_id parameter required' }, { status: 400 })
    }

    const response = await fetch(`${process.env.AI_AGENT_SERVICE_URL || 'http://localhost:8001'}/search/?query=${encodeURIComponent(query)}&workspace_id=${workspaceId}`)
    
    if (!response.ok) {
      return NextResponse.json({ detail: 'Search failed' }, { status: response.status })
    }

    const results = await response.json()
    return NextResponse.json(results)

  } catch (error) {
    console.error('Search error:', error)
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 })
  }
}