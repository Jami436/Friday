"""Vosk model loading shared by the wake keyword spotter and STT adapter."""
import threading
from pathlib import Path

MODEL_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data"
    / "models"
    / "vosk-model-small-en-us-0.15"
)

_model = None
_lock = threading.Lock()


def get_vosk_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from vosk import Model

                if not MODEL_DIR.is_dir():
                    raise FileNotFoundError(
                        f"Vosk model not found at {MODEL_DIR}. "
                        "Run: python scripts/download_vosk_model.py"
                    )
                _model = Model(str(MODEL_DIR))
    return _model
