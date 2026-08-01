const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

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

export interface MovieDetail {
  id: string; title: string; tagline?: string | null; overview: string; year: string;
  runtime?: string | null; rating?: string | null; genres: string[]; director?: string | null;
  cast: string[]; backdrop?: string | null; dominant_emotion?: string | null; match: number;
  emotional_arc: { time: string; tension: number; awe: number; action: number }[];
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

export interface ReviewItem {
  id: string;
  user_id: string;
  movie_id: string;
  rating: number;
  text: string;
  created_at: string;
  updated_at: string;
  is_owner: boolean;
}

export interface ReviewListResponse {
  items: ReviewItem[];
  page: number;
  limit: number;
  total: number;
  pages: number;
  average_rating: number;
  rating_count: number;
}

export async function apiRequest(endpoint: string, options: RequestInit = {}) {
  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
  
  const headers = new Headers(options.headers);
  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  try {
    if (typeof window !== 'undefined' && (window as any).Clerk) {
      const session = (window as any).Clerk.session;
      if (session) {
        const token = await session.getToken();
        if (token) {
          headers.set('Authorization', `Bearer ${token}`);
        }
      }
    }
  } catch (err) {
    console.warn("Clerk token extraction failed:", err);
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `API error: ${response.statusText}`);
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
    },
  });
  if (!response.ok) {
    let message = `API Error: ${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (typeof body?.detail === 'string') message = body.detail;
    } catch {}
    throw new ApiError(message, response.status);
  }

  return response.json();
}

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
      if (typeof body?.detail === 'string') message = body.detail;
    } catch {}
    throw new ApiError(message, response.status);
  }

  return response.json();
}

async function reviewRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `API Error: ${response.status}`);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export function fetchMovieReviews(movieId: string, page = 1, limit = 10) {
  return reviewRequest<ReviewListResponse>(
    `/movies/${encodeURIComponent(movieId)}/reviews?page=${page}&limit=${limit}`,
  );
}

export function createMovieReview(
  movieId: string,
  token: string,
  payload: { rating: number; text: string },
) {
  return reviewRequest<ReviewItem>(`/movies/${encodeURIComponent(movieId)}/reviews`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
}

export function updateMovieReview(
  reviewId: string,
  token: string,
  payload: { rating?: number; text?: string },
) {
  return reviewRequest<ReviewItem>(`/reviews/${reviewId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
}

export function deleteMovieReview(reviewId: string, token: string) {
  return reviewRequest<void>(`/reviews/${reviewId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  });
}
