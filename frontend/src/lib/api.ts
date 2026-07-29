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

export interface GenrePreference {
  genre: string;
  score: number;
}

export interface ProfileStats {
  movies_watched: number;
  reviews: number;
  genre_preferences: GenrePreference[];
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

export interface MovieCastMember {
  id: number;
  name: string;
  character?: string | null;
}

export interface MovieDetail {
  id: string;
  title: string;
  tagline: string;
  overview: string;
  release_date?: string | null;
  runtime?: number | null;
  certification?: string | null;
  genres: string[];
  director?: string | null;
  cast: MovieCastMember[];
  backdrop_path?: string | null;
  poster_path?: string | null;
  vote_average: number;
  match_score: number;
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export async function fetchMovieDetail(id: string): Promise<MovieDetail> {
  const response = await fetch(`${API_BASE_URL}/movies/${encodeURIComponent(id)}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
export async function fetchProfileStats(token: string): Promise<ProfileStats> {
  const response = await fetch(`${API_BASE_URL}/profile/stats`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    let message = `API Error: ${response.status} ${response.statusText}`;

    try {
      const body = await response.json();
      if (typeof body?.detail === 'string') {
        message = body.detail;
      }
    } catch {
      // Keep the status-based fallback message.
    }

    throw new ApiError(message, response.status);
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}
