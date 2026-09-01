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
        self._last_actions = False

    def _apply_actions(self, user_text: str) -> list[str]:
        confirmations: list[str] = []
        actions = self._extractor.extract(user_text)
        self._last_actions = bool(actions)
        for action in actions:
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
            elif action_type == "complete":
                title = (action.get("title") or "").strip()
                target = (action.get("target") or "task").strip().lower()
                if title:
                    found = False
                    if target == "deadline":
                        item_id = self._find_deadline_id(title)
                        if item_id is not None:
                            found = self._store.complete_deadline(item_id)
                    else:
                        item_id = self._find_task_id(title)
                        if item_id is not None:
                            found = self._store.complete_task(item_id)
                    if found:
                        confirmations.append(f"Marked '{title}' complete.")
                    else:
                        kind = "deadline" if target == "deadline" else "task"
                        confirmations.append(f"I couldn't find a matching {kind} for '{title}'.")
            elif action_type == "delete":
                title = (action.get("title") or "").strip()
                target = (action.get("target") or "task").strip().lower()
                if title:
                    found = False
                    if target == "deadline":
                        item_id = self._find_deadline_id(title)
                        if item_id is not None:
                            found = self._store.delete_deadline(item_id)
                    else:
                        item_id = self._find_task_id(title)
                        if item_id is not None:
                            found = self._store.delete_task(item_id)
                    if found:
                        confirmations.append(f"Deleted {target} '{title}'.")
                    else:
                        kind = "deadline" if target == "deadline" else "task"
                        confirmations.append(f"I couldn't find a matching {kind} for '{title}'.")
            elif action_type == "reschedule":
                title = (action.get("title") or "").strip()
                due = action.get("due") or ""
                if title and due:
                    item_id = self._find_deadline_id(title)
                    found = (
                        self._store.reschedule_deadline(
                            item_id, due, (action.get("time") or "") or ""
                        )
                        if item_id is not None
                        else False
                    )
                    if found:
                        confirmations.append(f"Rescheduled '{title}' to {due}.")
                    else:
                        confirmations.append(f"I couldn't find a matching deadline for '{title}'.")
            elif action_type == "list":
                target = (action.get("target") or "").strip().lower()
                confirmations.append(self._format_listing(target))
        return confirmations

    def _find_task_id(self, title: str) -> str | None:
        norm = title.lower().strip()
        for task in self._store.pending_tasks():
            if norm in task.title.lower() or task.title.lower() in norm:
                return task.id
        return None

    def _find_deadline_id(self, title: str) -> str | None:
        norm = title.lower().strip()
        for deadline in self._store.upcoming_deadlines(50):
            if norm in deadline.title.lower() or deadline.title.lower() in norm:
                return deadline.id
        return None

    def _format_listing(self, target: str) -> str:
        tasks = self._store.pending_tasks()
        deadlines = self._store.upcoming_deadlines(20)
        parts: list[str] = []
        if target in ("", "task") and tasks:
            items = "; ".join(f"{task.title}" for task in tasks)
            parts.append(f"You have {len(tasks)} pending task{'s' if len(tasks) != 1 else ''}: {items}.")
        elif target == "task":
            parts.append("You have no pending tasks.")
        if target in ("", "deadline") and deadlines:
            items = "; ".join(f"{d.title} ({d.due}{f' at {d.time}' if d.time else ''})" for d in deadlines)
            parts.append(f"You have {len(deadlines)} upcoming deadline{'s' if len(deadlines) != 1 else ''}: {items}.")
        elif target == "deadline":
            parts.append("You have no upcoming deadlines.")
        return " ".join(parts) or "There is nothing on your list right now."

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
