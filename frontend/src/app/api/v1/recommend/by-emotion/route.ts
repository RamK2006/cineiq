import { NextRequest, NextResponse } from 'next/server';
import { MOVIE_CATALOG } from '@/lib/catalog';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const emotion = searchParams.get('emotion') || '';
  const limit = parseInt(searchParams.get('limit') || '10', 10);

  const clean = emotion.toLowerCase().trim();
  let matches = MOVIE_CATALOG.filter(
    (m) =>
      m.dominant_emotion?.toLowerCase().includes(clean) ||
      m.genres.some((g) => g.toLowerCase().includes(clean))
  );

  if (matches.length === 0) {
    matches = MOVIE_CATALOG;
  }

  const movies = matches.slice(0, limit).map((m) => ({
    id: m.id,
    title: m.title,
    poster_path: m.poster_path,
    vote_average: m.vote_average,
    genres: m.genres,
    match_score: m.match_score,
  }));

  return NextResponse.json({
    algorithm: `emotion_${clean}`,
    movies,
  });
}
