"""Central application constants."""

AI_PROVIDER_GEMINI = "gemini"
AI_PROVIDER_LOCAL = "local"

MEMORY_BACKEND_SQLITE = "sqlite"
MEMORY_BACKEND_JSON = "json"

DEFAULT_AI_MODEL = "gemini-2.5-flash"

WAKE_KEYWORDS = ("friday",)

AUDIO_SAMPLE_RATE = 16000
AUDIO_BLOCK_SIZE = 1600  # 100 ms at 16 kHz
TTS_SAMPLE_RATE = 24000

GOODBYE_HINTS = (
    "goodbye",
    "bye friday",
    "bye boss",
    "that's all",
    "that's it",
    "stand down",
    "go to sleep",
    "go offline",
)

WAKE_WORD_ONLY = {"friday", "hey friday", "friday friday", "friday ", " yes friday"}
