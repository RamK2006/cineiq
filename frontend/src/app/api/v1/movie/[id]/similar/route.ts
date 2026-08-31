import { NextRequest, NextResponse } from 'next/server';
import { MOVIE_CATALOG, findMovieById } from '@/lib/catalog';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const { searchParams } = new URL(request.url);
  const limit = parseInt(searchParams.get('limit') || '8', 10);

  const target = findMovieById(id) || MOVIE_CATALOG[0];
  const targetGenres = new Set((target.genres || []).map((g) => g.toLowerCase()));

  const candidates = MOVIE_CATALOG.filter((m) => m.id !== id);

  const scored = candidates.map((m) => {
    const candGenres = new Set((m.genres || []).map((g) => g.toLowerCase()));
    let intersection = 0;
    targetGenres.forEach((g) => {
      if (candGenres.has(g)) intersection++;
    });
    const union = new Set([...targetGenres, ...candGenres]).size;
    const jaccard = union > 0 ? intersection / union : 0.0;
    const matchScore = round(0.6 * jaccard + 0.4 * m.match_score, 2);

    return {
      id: m.id,
      title: m.title,
      poster_path: m.poster_path,
      vote_average: m.match_score * 10,
      genres: m.genres,
      match_score: matchScore,
    };
  });

  scored.sort((a, b) => b.match_score - a.match_score);

  function round(val: number, decimals: number) {
    return Math.round(val * 100) / 100;
  }

  return NextResponse.json({
    movie_id: id,
    algorithm: 'hybrid_jaccard_similarity',
    movies: scored.slice(0, limit),
  });
}
