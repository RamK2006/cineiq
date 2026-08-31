import { NextRequest, NextResponse } from 'next/server';
import { MOVIE_CATALOG } from '@/lib/catalog';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const limit = parseInt(searchParams.get('limit') || '10', 10);
  const hours = searchParams.get('hours') || '24';

  const movies = MOVIE_CATALOG.slice(0, limit).map((m, idx) => {
    const views = Math.round(m.match_score * 1000);
    const clicks = Math.round(views * (0.3 - idx * 0.02));
    const ctr = round(clicks / max(views, 1), 2);
    return {
      movie_id: m.id,
      title: m.title,
      poster_path: m.poster_path,
      clicks,
      views,
      ctr,
    };
  });

  function max(a: number, b: number) { return a > b ? a : b; }
  function round(val: number, decimals: number) { return Math.round(val * 100) / 100; }

  return NextResponse.json({
    timeframe: `${hours}h`,
    movies,
  });
}
