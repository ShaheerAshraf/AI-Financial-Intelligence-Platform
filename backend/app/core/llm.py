from google import genai

from app.core.config import settings


def get_gemini_client() -> genai.Client:
    """Create a Gemini client from settings. No business logic."""
    if not settings.gemini_api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Add it to the project root .env file."
        )
    return genai.Client(api_key=settings.gemini_api_key)
