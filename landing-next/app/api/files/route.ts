import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const userId = searchParams.get('user_id')
    const workspaceId = searchParams.get('workspace_id')
    const limit = searchParams.get('limit') || '50'

    if (!userId) {
      return NextResponse.json({ detail: 'user_id parameter required' }, { status: 400 })
    }

    let url = `${process.env.INGESTION_SERVICE_URL || 'http://localhost:8000'}/files/?user_id=${userId}&limit=${limit}`
    if (workspaceId) {
      url += `&workspace_id=${workspaceId}`
    }

    const response = await fetch(url)
    
    if (!response.ok) {
      return NextResponse.json({ detail: 'Failed to fetch files' }, { status: response.status })
    }

    const files = await response.json()
    return NextResponse.json(files)

  } catch (error) {
    console.error('Files fetch error:', error)
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 })
  }
}