import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const userId = searchParams.get('user_id')

    if (!userId) {
      return NextResponse.json({ detail: 'user_id parameter required' }, { status: 400 })
    }

    const workspacesResponse = await fetch(`${process.env.INGESTION_SERVICE_URL || 'http://localhost:8000'}/workspaces/by-owner/${userId}`)
    const workspaces = workspacesResponse.ok ? await workspacesResponse.json() : []

    // Fetch files stats
    const filesResponse = await fetch(`${process.env.INGESTION_SERVICE_URL || 'http://localhost:8000'}/files/?user_id=${userId}&limit=1000`)
    const files = filesResponse.ok ? await filesResponse.json() : []

    // Calculate stats
    const stats = {
      total_files: files.length,
      processed_files: files.filter((f: any) => f.status === 2).length,
      processing_files: files.filter((f: any) => f.status === 1).length,
      error_files: files.filter((f: any) => f.status === 3).length,
      total_workspaces: workspaces.length
    }

    return NextResponse.json(stats)

  } catch (error) {
    console.error('Dashboard stats error:', error)
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 })
  }
}