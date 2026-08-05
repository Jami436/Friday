"""Vosk speaker verification: owner voice enrollment + cosine-similarity check.

Uses the Vosk speaker model (vosk-model-spk-0.4). FRIDAY computes a 128-dim
speaker embedding per utterance; enrollment averages several samples into a
reference profile, and verification compares a new utterance against it.
"""
import json
import threading
from pathlib import Path

import numpy as np

from app.core.logger import logger
from app.infrastructure.speech.vosk_model import get_vosk_model

SPK_MODEL_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data"
    / "models"
    / "vosk-model-spk-0.4"
)

_profile_lock = threading.Lock()


def _embedding(recognizer) -> list[float] | None:
    result = json.loads(recognizer.FinalResult())
    spk = result.get("spk")
    if not spk:
        return None
    return [float(x) for x in spk]


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


class VoskSpeakerVerifier:
    """Implements the SpeakerVerifier port against Vosk speaker embeddings."""

    def __init__(self, profile_path: Path | None = None) -> None:
        self._profile_path = profile_path or (
            Path(__file__).resolve().parent.parent.parent.parent
            / "data"
            / "memory"
            / "owner_profile.json"
        )
        self._reference: np.ndarray | None = None
        self._spk_model = None
        self._recognizer = None
        self._load_profile()

    # -- model lifecycle -------------------------------------------------

    def _ensure_models(self):
        if self._recognizer is not None:
            return
        from vosk import KaldiRecognizer, SpkModel

        if not SPK_MODEL_DIR.is_dir():
            raise FileNotFoundError(
                f"Speaker model not found at {SPK_MODEL_DIR}. "
                "Run: python scripts/download_vosk_model.py --speaker"
            )
        self._spk_model = SpkModel(str(SPK_MODEL_DIR))
        self._recognizer = KaldiRecognizer(get_vosk_model(), 16000)
        self._recognizer.SetSpkModel(self._spk_model)

    # -- profile persistence --------------------------------------------

    def _load_profile(self) -> None:
        try:
            if self._profile_path.exists():
                data = json.loads(self._profile_path.read_text(encoding="utf-8"))
                vec = data.get("embedding")
                if vec:
                    self._reference = np.asarray(vec, dtype=np.float64)
        except (OSError, json.JSONDecodeError, ValueError):
            logger.warning("Could not load owner voice profile; treating as un-enrolled.")

    def _save_profile(self) -> None:
        self._profile_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "embedding": self._reference.tolist() if self._reference is not None else None,
        }
        self._profile_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # -- SpeakerVerifier port --------------------------------------------

    def is_enrolled(self) -> bool:
        return self._reference is not None

    def enroll(self, samples: list[np.ndarray]) -> None:
        """Compute the mean speaker embedding across enrollment samples."""
        self._ensure_models()
        vectors = []
        for audio in samples:
            if audio.size == 0:
                continue
            self._recognizer.Reset()
            self._recognizer.AcceptWaveform(audio.tobytes())
            spk = _embedding(self._recognizer)
            if spk:
                vectors.append(np.asarray(spk, dtype=np.float64))
        if not vectors:
            raise ValueError("No valid speaker embeddings could be extracted from the samples.")
        with _profile_lock:
            self._reference = np.mean(np.stack(vectors), axis=0)
            self._save_profile()
        logger.info(f"Owner voice enrolled from {len(vectors)} sample(s).")

    def verify(self, audio: np.ndarray) -> float:
        if not self.is_enrolled():
            return 0.0
        if audio.size == 0:
            return 0.0
        self._ensure_models()
        self._recognizer.Reset()
        self._recognizer.AcceptWaveform(audio.tobytes())
        spk = _embedding(self._recognizer)
        if not spk:
            return 0.0
        return _cosine(self._reference, np.asarray(spk, dtype=np.float64))
