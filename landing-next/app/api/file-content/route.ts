import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const s3Key = searchParams.get('s3_key')

    if (!s3Key) {
      return NextResponse.json({ detail: 's3_key parameter required' }, { status: 400 })
    }

    const response = await fetch(`${process.env.INGESTION_SERVICE_URL || 'http://localhost:8000'}/file-content/?s3_key=${encodeURIComponent(s3Key)}`)
    
    if (!response.ok) {
      return NextResponse.json({ detail: 'Failed to fetch file content' }, { status: response.status })
    }

    const content = await response.json()
    return NextResponse.json(content)

  } catch (error) {
    console.error('File content fetch error:', error)
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 })
  }
}