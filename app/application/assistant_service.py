"""Application service: the FRIDAY assistant use case."""
from dataclasses import dataclass, field

from app.application.briefing_service import BriefingService
from app.application.memory_extractor import MemoryExtractor
from app.domain.entities.conversation import ChatMessage
from app.domain.ports.ai import AIProvider
from app.domain.ports.clock import Clock
from app.domain.ports.memory import MemoryStore
from app.domain.services.persona import build_system_prompt

MAX_HISTORY_TURNS = 10


@dataclass
class AssistantReply:
    """The assistant's spoken reply plus any actions it performed."""

    text: str
    confirmations: list[str] = field(default_factory=list)


class AssistantService:
    """Turns user text into a FRIDAY reply, persisting tasks/deadlines/notes."""

    def __init__(
        self,
        ai: AIProvider,
        store: MemoryStore,
        briefing: BriefingService,
        clock: Clock,
        extractor: MemoryExtractor | None = None,
    ) -> None:
        self._ai = ai
        self._store = store
        self._briefing = briefing
        self._clock = clock
        self._extractor = extractor or MemoryExtractor(ai)
        self._history: list[ChatMessage] = []

    def _apply_actions(self, user_text: str) -> list[str]:
        confirmations: list[str] = []
        for action in self._extractor.extract(user_text):
            action_type = action.get("type")
            if action_type == "deadline":
                title = (action.get("title") or "").strip()
                due = action.get("due") or ""
                if title and due:
                    self._store.add_deadline(title, due, (action.get("time") or "") or "")
                    confirmations.append(f"Deadline saved: {title} ({due}).")
            elif action_type == "task":
                title = (action.get("title") or "").strip()
                if title:
                    self._store.add_task(title)
                    confirmations.append(f"Task added: {title}.")
            elif action_type == "note":
                text = (action.get("text") or "").strip()
                if text:
                    self._store.add_note(text)
                    confirmations.append("Noted.")
        return confirmations

    def respond(self, user_text: str) -> AssistantReply:
        self._history.append(ChatMessage(role="user", text=user_text))
        if len(self._history) > MAX_HISTORY_TURNS * 2:
            self._history = self._history[-MAX_HISTORY_TURNS * 2:]

        confirmations = self._apply_actions(user_text)

        system = build_system_prompt(
            daily_context=self._briefing.build_daily_context(),
            now=self._clock.now(),
        )
        reply = self._ai.chat(
            history=self._history,
            system_instruction=system,
            temperature=0.7,
        )
        self._history.append(ChatMessage(role="model", text=reply))
        return AssistantReply(text=reply, confirmations=confirmations)

    def reset_history(self) -> None:
        self._history = []
