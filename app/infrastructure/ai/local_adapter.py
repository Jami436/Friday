"""Placeholder adapter for local models. Register local providers here as they land."""
from app.core.exceptions import AIProviderError
from app.domain.entities.conversation import ChatMessage
from app.domain.ports.ai import AIProvider


class LocalAdapter(AIProvider):
    """Reserved for on-device models. Not implemented yet."""

    def generate_response(self, prompt: str) -> str:
        raise AIProviderError(
            "Local AI provider is not implemented yet. Set AI_PROVIDER=gemini in .env."
        )

    def chat(
        self,
        history: list[ChatMessage],
        system_instruction: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        raise AIProviderError(
            "Local AI provider is not implemented yet. Set AI_PROVIDER=gemini in .env."
        )
