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

    def generate_response(self, prompt: str) -> str:
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
            )
        except errors.APIError as error:
            raise AIProviderError(
                f"Gemini API error (status={error.status}): {error.message}"
            ) from error
        return response.text or ""

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
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=self._to_wire(history),
                config=config,
            )
        except errors.APIError as error:
            raise AIProviderError(
                f"Gemini API error (status={error.status}): {error.message}"
            ) from error
        return response.text or ""
