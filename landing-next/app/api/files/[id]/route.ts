import { NextRequest, NextResponse } from 'next/server'

export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const response = await fetch(`${process.env.INGESTION_SERVICE_URL || 'http://localhost:8000'}/files/${params.id}`, {
      method: 'DELETE'
    })
    
    if (!response.ok) {
      return NextResponse.json({ detail: 'Failed to delete file' }, { status: response.status })
    }

    const result = await response.json()
    return NextResponse.json(result)

  } catch (error) {
    console.error('File deletion error:', error)
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 })
  }
}