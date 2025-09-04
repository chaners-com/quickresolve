import { NextRequest, NextResponse } from 'next/server'

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const response = await fetch(`${process.env.INGESTION_SERVICE_URL || 'http://localhost:8000'}/files/${params.id}/status`)
    
    if (!response.ok) {
      return NextResponse.json({ detail: 'Failed to fetch file status' }, { status: response.status })
    }

    const status = await response.json()
    return NextResponse.json(status)

  } catch (error) {
    console.error('File status fetch error:', error)
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 })
  }
}
