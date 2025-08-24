import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { messages, workspace_id } = body

    const response = await fetch(`${process.env.AI_AGENT_SERVICE_URL || 'http://localhost:8001'}/conversation`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        messages,
        workspace_id
      })
    })

    if (!response.ok) {
      const error = await response.json()
      return NextResponse.json({ detail: error.detail || 'AI conversation failed' }, { status: response.status })
    }

    const result = await response.json()
    return NextResponse.json(result)

  } catch (error) {
    console.error('AI conversation error:', error)
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 })
  }
}