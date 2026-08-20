from google.genai import types
from pydantic import BaseModel

from app.core.config import settings
from app.core.llm import get_gemini_client


def generate_structured(
    *,
    system_instruction: str,
    user_content: str,
    response_model: type[BaseModel],
) -> BaseModel:
    """Shared Gemini structured-output helper used by all agents."""
    client = get_gemini_client()

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_json_schema=response_model.model_json_schema(),
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            ),
        ),
    )

    if not response.text:
        raise ValueError("Gemini returned an empty response")

    return response_model.model_validate_json(response.text)
