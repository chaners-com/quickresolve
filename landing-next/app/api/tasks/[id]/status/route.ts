import { NextRequest, NextResponse } from 'next/server'

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const response = await fetch(`${process.env.TASK_SERVICE_URL || 'http://localhost:8010'}/task/${params.id}/status`, {
      cache: 'no-store'
    })

    if (!response.ok) {
      return NextResponse.json({ detail: 'Failed to fetch task status' }, { status: response.status })
    }

    const status = await response.json()
    return NextResponse.json(status)

  } catch (error) {
    console.error('Task status fetch error:', error)
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 })
  }
}
