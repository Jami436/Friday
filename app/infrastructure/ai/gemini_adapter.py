"""Gemini adapter for the AIProvider port."""
from google import genai
from google.genai import errors

from app.core.exceptions import AIProviderError
from app.domain.entities.conversation import ChatMessage
from app.domain.ports.ai import AIProvider


class GeminiAdapter(AIProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    @staticmethod
    def _to_wire(history: list[ChatMessage]) -> list[dict]:
        return [
            {"role": message.role, "parts": [{"text": message.text}]}
            for message in history
        ]

    def _response_text(self, model: str, contents, config: dict | None = None) -> str:
        """Generate content and wrap any failure in an AIProviderError."""
        try:
            response = self._client.models.generate_content(
                model=model, contents=contents, config=config
            )
        except errors.APIError as error:
            raise AIProviderError(
                f"Gemini API error (status={getattr(error, 'status', 'unknown')}): {error.message}"
            ) from error
        except Exception as error:  # surface network/other SDK failures
            raise AIProviderError(f"Gemini request failed: {error}") from error
        return response.text or ""

    def generate_response(self, prompt: str) -> str:
        return self._response_text(self._model, prompt)

    def chat(
        self,
        history: list[ChatMessage],
        system_instruction: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        config: dict = {}
        if system_instruction:
            config["system_instruction"] = system_instruction
        if temperature is not None:
            config["temperature"] = temperature
        return self._response_text(self._model, self._to_wire(history), config)
