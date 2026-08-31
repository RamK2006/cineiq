import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { event_type, movie_id, source } = body;

    if (!event_type || !movie_id) {
      return NextResponse.json({ detail: 'event_type and movie_id are required' }, { status: 400 });
    }

    return NextResponse.json({
      status: 'queued',
      event_type,
      movie_id,
      source: source || 'recommended',
    });
  } catch (e) {
    return NextResponse.json({ detail: 'Invalid JSON payload' }, { status: 400 });
  }
}
