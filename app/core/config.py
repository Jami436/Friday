from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.exceptions import ConfigurationError

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """
    Application settings.
    """

    app_name: str = "FRIDAY"
    app_version: str = "0.1.0"
    debug: bool = True

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    ai_provider: str = "gemini"
    memory_backend: str = "sqlite"

    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    elevenlabs_stability: float | None = None
    elevenlabs_similarity_boost: float | None = None
    elevenlabs_max_retries: int = 3

    gmail_user: str = ""
    gmail_app_password: str = ""

    audio_input_device: int | None = None
    audio_output_device: int | None = None

    wake_clap_min_count: int = 2
    wake_clap_window_sec: float = 1.8
    listen_max_sec: float = 12.0
    listen_silence_sec: float = 1.2

    # Security / owner identity (per-installation: each machine's owner binds
    # their own voice enrollment + passphrase in their local setup)
    owner_name: str = "Boss"
    security_enabled: bool = False
    security_mode: str = "voice"  # voice | passphrase | both
    security_passphrase: str = ""
    speaker_threshold: float = 0.72

    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        # Prefer .env over inherited process environment variables so a stale
        # GEMINI_API_KEY (or other key) in the parent environment cannot shadow
        # the valid value stored in the project .env file.
        return init_settings, dotenv_settings, env_settings

    @model_validator(mode="after")
    def _validate_gemini_api_key(self) -> "Settings":
        key = self.gemini_api_key.strip()

        if not key:
            raise ConfigurationError(
                "GEMINI_API_KEY is not set. "
                "Add GEMINI_API_KEY=<your key> to the .env file or environment. "
                "Create one at https://aistudio.google.com/app/apikey"
            )

        if len(key) < 20 or any(ch.isspace() for ch in key):
            raise ConfigurationError(
                "GEMINI_API_KEY does not look like a valid key. "
                "Copy the full key with no spaces or quotes. "
                f"(received '{key[:10]}...{key[-4:]}' with {len(key)} characters)."
            )

        self.gemini_api_key = key
        return self


settings = Settings()
