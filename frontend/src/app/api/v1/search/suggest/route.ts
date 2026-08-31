import { NextRequest, NextResponse } from 'next/server';
import { searchCatalog } from '@/lib/catalog';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const query = searchParams.get('q') || '';
  const limit = parseInt(searchParams.get('limit') || '5', 10);

  const q = query.toLowerCase().trim();
  if (!q) {
    return NextResponse.json([]);
  }

  const matches = searchCatalog(q, limit * 2);
  const sorted = matches
    .sort((a, b) => {
      const aStartsWith = a.title.toLowerCase().startsWith(q);
      const bStartsWith = b.title.toLowerCase().startsWith(q);
      if (aStartsWith && !bStartsWith) return -1;
      if (!aStartsWith && bStartsWith) return 1;
      return 0;
    })
    .slice(0, limit);

  const suggestions = sorted.map((m) => ({
    id: m.id,
    title: m.title,
    poster_path: m.poster_path,
    year: m.year ? parseInt(m.year, 10) : null,
  }));

  return NextResponse.json(suggestions);
}
