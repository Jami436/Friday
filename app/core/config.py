from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings.
    """

    app_name: str = "FRIDAY"
    app_version: str = "0.1.0"
    debug: bool = True

    gemini_api_key: str

    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()