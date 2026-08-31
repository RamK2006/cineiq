/**
 * CineBot API Client
 * Handles communication with the backend AI assistant endpoint.
 */

export interface CineBotMessage {
  role: 'user' | 'assistant';
  content: string;
  recommendations?: {
    id: string;
    title: string;
    overview: string;
    poster_path: string | null;
    reasoning: string;
  }[];
}

export async function fetchCineBotResponse(
  message: string,
  history: Omit<CineBotMessage, 'recommendations'>[]
): Promise<CineBotMessage> {
  const response = await fetch('/api/v1/search/assistant', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
      history: history.map(h => ({ role: h.role, content: h.content })),
    }),
  });

  if (!response.ok) {
    throw new Error('Failed to fetch CineBot response');
  }

  const data = await response.json();
  
  return {
    role: 'assistant',
    content: data.conversational_reply,
    recommendations: data.recommendations,
  };
}
