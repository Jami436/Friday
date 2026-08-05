"""Composition root: the only place that wires domain ports to infrastructure adapters."""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.application.access_control import AccessControlService
from app.application.assistant_service import AssistantService
from app.application.briefing_service import BriefingService
from app.application.conversation_service import ConversationService
from app.application.memory_extractor import MemoryExtractor
from app.application.reminder_service import ReminderService
from app.core.config import Settings, settings as default_settings
from app.core.constants import (
    AI_PROVIDER_GEMINI,
    AI_PROVIDER_LOCAL,
    MEMORY_BACKEND_JSON,
    MEMORY_BACKEND_SQLITE,
)
from app.core.exceptions import ConfigurationError
from app.core.lifecycle import ApplicationLifecycle
from app.core.logger import logger
from app.domain.ports.ai import AIProvider
from app.domain.ports.audio import AudioOutput, AudioStream
from app.domain.ports.clock import Clock
from app.domain.ports.email import EmailProvider
from app.domain.ports.memory import MemoryStore
from app.domain.ports.security import PassphraseStore, SpeakerVerifier
from app.domain.ports.speech import SpeechToText, TextToSpeech, VoiceActivityDetector, WakeDetector, WakeEngine
from app.domain.services.clock import SystemClock
from app.infrastructure.ai.gemini_adapter import GeminiAdapter
from app.infrastructure.ai.local_adapter import LocalAdapter
from app.infrastructure.audio.clap_detector import ClapDetector
from app.infrastructure.audio.sounddevice_audio import SounddeviceAudioOutput, SounddeviceMicrophone
from app.infrastructure.audio.vad import SounddeviceVoiceActivityDetector
from app.infrastructure.audio.wake_engine import SounddeviceWakeEngine
from app.infrastructure.email.gmail_imap import GmailImapAdapter
from app.infrastructure.persistence.json_store import JsonMemoryStore
from app.infrastructure.persistence.sqlite_store import SqliteMemoryStore
from app.infrastructure.security.passphrase_store import FilePassphraseStore
from app.infrastructure.security.vosk_speaker import VoskSpeakerVerifier
from app.infrastructure.speech.console_tts import ConsoleTextToSpeech
from app.infrastructure.speech.elevenlabs_tts import ElevenLabsTextToSpeech
from app.infrastructure.speech.local_tts import SystemSpeechTextToSpeech
from app.infrastructure.speech.vosk_keyword import VoskKeywordSpotter
from app.infrastructure.speech.vosk_stt import VoskSpeechToText

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "memory"


@dataclass(frozen=True)
class Container:
    settings: Settings
    clock: Clock
    lifecycle: ApplicationLifecycle
    ai: AIProvider
    store: MemoryStore
    email: EmailProvider
    audio_output: AudioOutput
    tts: TextToSpeech
    stt: SpeechToText
    vad: VoiceActivityDetector
    wake_engine: WakeEngine
    extractor: MemoryExtractor
    briefing: BriefingService
    assistant: AssistantService
    reminders: ReminderService
    conversation: ConversationService
    verifier: SpeakerVerifier
    passphrase_store: PassphraseStore
    access_control: AccessControlService


def _build_ai(settings: Settings) -> AIProvider:
    provider = settings.ai_provider.strip().lower()
    if provider == AI_PROVIDER_GEMINI:
        return GeminiAdapter(api_key=settings.gemini_api_key, model=settings.gemini_model)
    if provider == AI_PROVIDER_LOCAL:
        return LocalAdapter()
    raise ConfigurationError(
        f"Unknown AI_PROVIDER={provider!r}. Use 'gemini' or 'local'."
    )


def _build_store(settings: Settings) -> MemoryStore:
    backend = settings.memory_backend.strip().lower()
    if backend == MEMORY_BACKEND_SQLITE:
        return SqliteMemoryStore(DATA_DIR / "friday.db")
    if backend == MEMORY_BACKEND_JSON:
        return JsonMemoryStore(DATA_DIR / "friday_data.json")
    raise ConfigurationError(
        f"Unknown MEMORY_BACKEND={backend!r}. Use 'sqlite' or 'json'."
    )


def _build_tts(settings: Settings, audio_output: AudioOutput) -> TextToSpeech:
    if settings.elevenlabs_api_key:
        return ElevenLabsTextToSpeech(
            api_key=settings.elevenlabs_api_key,
            audio_output=audio_output,
            voice_id=settings.elevenlabs_voice_id,
        )
    try:
        return SystemSpeechTextToSpeech()
    except Exception as error:  # noqa: BLE001 - voice is optional
        logger.warning(f"System speech unavailable; using console output: {error}")
        return ConsoleTextToSpeech()


def _build_wake_engine(settings: Settings) -> WakeEngine:
    stream_factory: Callable[[], AudioStream] = lambda: SounddeviceMicrophone(settings.audio_input_device)
    clap_factory: Callable[[], WakeDetector] = lambda: ClapDetector(
        min_count=settings.wake_clap_min_count,
        window_sec=settings.wake_clap_window_sec,
    )
    return SounddeviceWakeEngine(
        stream_factory=stream_factory,
        clap_detector_factory=clap_factory,
        keyword_spotter_factory=VoskKeywordSpotter,
    )


def build_container(settings: Settings | None = None, **overrides) -> Container:
    """Build the fully-wired application.

    Pass a test ``Settings`` to override config, and/or keyword overrides such as
    ``ai=FakeAI()`` to substitute specific components (DI test seam).
    """
    config = settings or default_settings

    components = {
        "settings": config,
        "clock": SystemClock(),
        "lifecycle": ApplicationLifecycle(),
        "ai": _build_ai(config),
        "store": _build_store(config),
        "email": GmailImapAdapter(user=config.gmail_user, app_password=config.gmail_app_password),
        "audio_output": SounddeviceAudioOutput(device=config.audio_output_device),
        "stt": VoskSpeechToText(),
        "vad": SounddeviceVoiceActivityDetector(
            device=config.audio_input_device,
            default_max_sec=config.listen_max_sec,
            default_silence_sec=config.listen_silence_sec,
        ),
        "wake_engine": _build_wake_engine(config),
    }
    components["tts"] = _build_tts(config, components["audio_output"])

    components.update(overrides)

    components["extractor"] = MemoryExtractor(components["ai"], clock=components["clock"])
    components["briefing"] = BriefingService(
        store=components["store"], email=components["email"], clock=components["clock"]
    )
    components["assistant"] = AssistantService(
        ai=components["ai"],
        store=components["store"],
        briefing=components["briefing"],
        clock=components["clock"],
        extractor=components["extractor"],
    )
    components["reminders"] = ReminderService(
        store=components["store"], tts=components["tts"], clock=components["clock"]
    )
    components["conversation"] = ConversationService(
        assistant=components["assistant"],
        tts=components["tts"],
        stt=components["stt"],
        vad=components["vad"],
        clock=components["clock"],
    )
    components["verifier"] = VoskSpeakerVerifier()
    components["passphrase_store"] = FilePassphraseStore()
    components["access_control"] = AccessControlService(
        verifier=components["verifier"],
        passphrase_store=components["passphrase_store"],
        vad=components["vad"],
        stt=components["stt"],
        tts=components["tts"],
        clock=components["clock"],
        enabled=config.security_enabled,
        mode=config.security_mode,
        threshold=config.speaker_threshold,
        passphrase=config.security_passphrase,
        owner_name=config.owner_name,
    )

    return Container(**components)
