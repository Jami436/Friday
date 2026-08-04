"""Console adapter for the TextToSpeech port (no audio hardware needed)."""
from app.core.logger import logger
from app.domain.ports.speech import TextToSpeech


class ConsoleTextToSpeech(TextToSpeech):
    """Prints FRIDAY's speech to the log instead of playing audio."""

    def speak(self, text: str) -> None:
        logger.info(f"[FRIDAY] {text}")
