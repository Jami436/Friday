"""Passphrase store: owner passphrase persisted per-installation."""
import json
from pathlib import Path

from app.domain.ports.security import PassphraseStore


class FilePassphraseStore(PassphraseStore):
    """Stores the owner's passphrase in data/memory/owner_secret.json.

    The passphrase is compared against a transcription of what the speaker
    says; exact normalized match grants access.
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (
            Path(__file__).resolve().parent.parent.parent.parent
            / "data"
            / "memory"
            / "owner_secret.json"
        )

    def get(self) -> str:
        if not self._path.exists():
            return ""
        try:
            return json.loads(self._path.read_text(encoding="utf-8")).get("passphrase", "")
        except (OSError, json.JSONDecodeError, ValueError):
            return ""

    def set(self, passphrase: str) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps({"passphrase": passphrase}, indent=2),
            encoding="utf-8",
        )
