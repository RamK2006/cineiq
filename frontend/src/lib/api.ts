const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api/v1';

export interface MovieItem {
  id: string;
  title: string;
  poster_path?: string | null;
  vote_average: number;
  genres: string[];
  match_score: number;
}

export interface RecommendationResponse {
  algorithm: string;
  movies: MovieItem[];
}

export async function fetchTrendingMovies(limit: number = 20): Promise<RecommendationResponse> {
  const response = await fetch(`${API_BASE_URL}/recommend/trending?limit=${limit}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

export async function fetchPersonalizedMovies(limit: number = 20): Promise<RecommendationResponse> {
  const response = await fetch(`${API_BASE_URL}/recommend/personalized?limit=${limit}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}
