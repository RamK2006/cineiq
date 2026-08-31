"""
CineBot LLM Service Module
Handles interactions with the Google Gemini API for conversational movie recommendations.
Uses the official google-genai SDK with function calling and structured outputs.
"""
import os
import json
import structlog
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

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
    Generates a conversational response and movie recommendations using Google Gemini (`gemini-2.0-flash`).
    Utilizes structured Pydantic output schemas for guaranteed parseable responses.
    """
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("gemini_api_key_missing", message="GEMINI_API_KEY is not set. CineBot fallback triggered.")
            return CineBotResponse(
                conversational_reply="I'm currently running in offline mode. Please configure the GEMINI_API_KEY environment variable to enable AI recommendations!",
                recommendations=[]
            )

        client = genai.Client(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

        # Format conversation history using the google-genai Content types
        formatted_contents = []
        for msg in conversation_history[-5:]:
            role = "user" if msg.get("role") == "user" else "model"
            formatted_contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg.get("content", ""))]
                )
            )

        # Append current user prompt along with the catalog context
        augmented_prompt = f"""Available Movies Catalog Context (ID, Title, Genre, Overview):
{available_movies_context}

User's Latest Message:
{user_message}"""

        formatted_contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=augmented_prompt)]
            )
        )

        config = types.GenerateContentConfig(
            system_instruction=(
                "You are CineBot, an expert AI movie recommendation assistant for the CineIQ platform. "
                "Your goal is to suggest up to 3 movies from the provided catalog that match the user's natural language query. "
                "Always provide a friendly, conversational reply alongside structured recommendations."
            ),
            response_mime_type="application/json",
            response_schema=CineBotResponse,
            temperature=0.7,
        )

        response = client.models.generate_content(
            model=model_name,
            contents=formatted_contents,
            config=config,
        )

        if not response.text:
            raise ValueError("Empty response received from Gemini model.")

        result = json.loads(response.text)
        return CineBotResponse(**result)

    except Exception as e:
        logger.error("cinebot_generation_failed", error=str(e))
        return CineBotResponse(
            conversational_reply="I'm having trouble connecting to my movie database right now. Please try again in a moment!",
            recommendations=[]
        )
