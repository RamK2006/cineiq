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

export interface RadarItem {
  subject: string;
  A: number;
  fullMark: number;
}

export interface ProfileStats {
  movies_watched: number;
  reviews: number;
  genre_preferences: GenrePreference[];
  radarData?: RadarItem[];
  summaryMessage?: string;
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
  helpful_count?: number;
  user_vote?: number;
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

export async function fetchTrendingMovies(limit: number = 20): Promise<RecommendationResponse> {
  return apiRequest(`/recommend/trending?limit=${limit}`);
}

export async function fetchMovie(movieId: string): Promise<MovieDetail> {
  return apiRequest(`/movie/${encodeURIComponent(movieId)}`);
}

export async function fetchPersonalizedMovies(limit: number = 20): Promise<RecommendationResponse> {
  return apiRequest(`/recommend/personalized?limit=${limit}`);
}

export async function fetchMoviesByEmotion(emotion: string, limit: number = 10): Promise<RecommendationResponse> {
  return apiRequest(`/recommend/by-emotion?emotion=${encodeURIComponent(emotion)}&limit=${limit}`);
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
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
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

export function voteMovieReview(
  reviewId: string,
  token: string,
  voteType: number,
) {
  return reviewRequest<{ message: string; user_vote: number }>(`/reviews/${reviewId}/vote`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ vote_type: voteType }),
  });
}

export async function trackAnalyticsEvent(payload: {
  event_type: 'view' | 'click' | 'trailer_play';
  movie_id: string;
  source?: string;
  user_id?: string;
}) {
  return apiRequest('/analytics/event', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function fetchTopClickedMovies(hours = 24, limit = 10) {
  return apiRequest(`/analytics/top-clicked?hours=${hours}&limit=${limit}`);
}

