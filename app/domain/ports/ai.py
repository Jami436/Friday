"""Port for the AI conversation brain. Implementations are interchangeable."""
from abc import ABC, abstractmethod

from app.domain.entities.conversation import ChatMessage


class AIProvider(ABC):
    """Generates assistant replies. The model is an implementation detail."""

    @abstractmethod
    def generate_response(self, prompt: str) -> str:
        """One-shot completion for a single prompt (e.g. structured extraction)."""
        raise NotImplementedError

    @abstractmethod
    def chat(
        self,
        history: list[ChatMessage],
        system_instruction: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """Conversation with a system prompt and turn history."""
        raise NotImplementedError
