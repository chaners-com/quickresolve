import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const workspaceId = searchParams.get('workspace_id')

    if (!workspaceId) {
      return NextResponse.json({ detail: 'workspace_id parameter required' }, { status: 400 })
    }

    const formData = await request.formData()
    
    const response = await fetch(`${process.env.INGESTION_SERVICE_URL || 'http://localhost:8000'}/uploadfile/?workspace_id=${workspaceId}`, {
      method: 'POST',
      body: formData
    })

    if (!response.ok) {
      const error = await response.json()
      return NextResponse.json({ detail: error.detail || 'Upload failed' }, { status: response.status })
    }

    const result = await response.json()
    
    // Forward the Location header for status polling
    const location = response.headers.get('Location')
    const nextResponse = NextResponse.json(result, { status: response.status })
    if (location) {
      nextResponse.headers.set('Location', location)
    }
    
    return nextResponse

  } catch (error) {
    console.error('Upload error:', error)
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 })
  }
}
