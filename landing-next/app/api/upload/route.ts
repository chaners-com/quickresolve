import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const workspaceId = searchParams.get('workspace_id')

    if (!workspaceId) {
      return NextResponse.json({ detail: 'workspace_id parameter required' }, { status: 400 })
    }

    const formData = await request.formData()
    
    const response = await fetch(`${process.env.INGESTION_SERVICE_URL || 'http://localhost:8000'}/uploadfile?workspace_id=${workspaceId}`, {
      method: 'POST',
      body: formData
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      return NextResponse.json({ detail: error.detail || 'Upload failed' }, { status: response.status })
    }

    // Ingestion replies 202 with an empty body and a Location header pointing
    // to the task-service status URL (http://localhost:8010/task/<id>/status).
    // Rewrite it to our own proxy so the browser never talks to task-service.
    const location = response.headers.get('Location')
    const taskId = location?.match(/\/task\/([^/]+)\/status/)?.[1]
    const statusUrl = taskId ? `/api/tasks/${taskId}/status` : null

    const nextResponse = NextResponse.json({ task_id: taskId, status_url: statusUrl }, { status: response.status })
    if (statusUrl) {
      nextResponse.headers.set('Location', statusUrl)
    }
    
    return nextResponse

  } catch (error) {
    console.error('Upload error:', error)
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 })
  }
}
