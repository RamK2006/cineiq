"""
CineBot LLM Service Module
Handles interactions with the Google Gemini API for conversational movie recommendations.
Uses structured output (JSON schema) to ensure consistent, parseable responses.
"""
import os
import json
import structlog
from typing import List, Dict, Optional
from pydantic import BaseModel, Field

logger = structlog.get_logger()

class MovieRecommendation(BaseModel):
    """Schema for a single movie recommendation returned by the LLM."""
    id: str = Field(description="The unique identifier of the movie")
    title: str = Field(description="The title of the movie")
    reasoning: str = Field(description="A brief explanation of why this movie matches the user's request")

class CineBotResponse(BaseModel):
    """Schema for the complete CineBot response."""
    conversational_reply: str = Field(description="A friendly, conversational response to the user's query")
    recommendations: List[MovieRecommendation] = Field(description="A list of recommended movies based on the query")

async def generate_cinebot_response(
    conversation_history: List[Dict[str, str]],
    user_message: str,
    available_movies_context: str
) -> Optional[CineBotResponse]:
    """
    Generates a conversational response and movie recommendations using Google Gemini.
    Uses function calling / structured output to ensure consistent formatting.
    """
    try:
        import google.generativeai as genai
        
        # Check if API key is configured
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("gemini_api_key_missing", message="GEMINI_API_KEY is not set. CineBot fallback triggered.")
            return CineBotResponse(
                conversational_reply="I'm currently running in offline mode. Please configure the GEMINI_API_KEY environment variable to enable AI recommendations!",
                recommendations=[]
            )

        genai.configure(api_key=api_key)
        
        # Use gemini-2.0-flash or fallback to gemini-1.5-flash
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": CineBotResponse,
            }
        )

        # Construct the prompt with conversation history and available movies context
        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-5:]])
        
        prompt = f"""You are CineBot, an expert AI movie recommendation assistant for the CineIQ platform.
Your goal is to suggest movies from the provided catalog that match the user's natural language query.

Available Movies Catalog Context (ID, Title, Genre, Overview):
{available_movies_context}

Conversation History:
{history_text}

User's Latest Message:
{user_message}

Instructions:
1. Analyze the user's request for genre, mood, themes, or specific movie references.
2. Select up to 3 movies from the provided catalog that best match the request.
3. Provide a friendly, conversational reply explaining your choices.
4. If no movies match, politely explain why and suggest a broader search.
5. STRICTLY output valid JSON matching the CineBotResponse schema. Do not include markdown formatting or extra text.
"""

        response = model.generate_content(prompt)
        
        # Parse the JSON response
        result = json.loads(response.text)
        return CineBotResponse(**result)

    except Exception as e:
        logger.error("cinebot_generation_failed", error=str(e))
        return CineBotResponse(
            conversational_reply="I'm having trouble connecting to my movie database right now. Please try again in a moment!",
            recommendations=[]
        )
