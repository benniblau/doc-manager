from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    MODEL_URL: str
    MODEL_NAME: str = "Qwen3.6"
    ENABLE_THINKING: bool = False
    MAX_TEXT_CHARS: int = 32000
    TEMPERATURE: float = 0.1
    REQUEST_TIMEOUT: int = 120
    MAX_AGENTS: int = 4

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @computed_field
    @property
    def model_base_url(self) -> str:
        """Ensure the URL ends with /v1 as required by the OpenAI-compatible API."""
        url = self.MODEL_URL.rstrip("/")
        if not url.endswith("/v1"):
            url = f"{url}/v1"
        return url


settings = Settings()
