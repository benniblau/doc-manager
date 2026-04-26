from typing import Optional

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

    VISION_MODEL_URL: Optional[str] = None
    VISION_MODEL_NAME: str = "qwen2.5vl:3b"
    VISION_REQUEST_TIMEOUT: int = 300  # vision inference is slow on edge hardware
    VISION_MAX_PAGES: int = 5          # cap pages sent to vision model per document
    VISION_NUM_CTX: int = 4096         # context window for vision inference

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @computed_field
    @property
    def model_base_url(self) -> str:
        url = self.MODEL_URL.rstrip("/")
        if not url.endswith("/v1"):
            url = f"{url}/v1"
        return url

    @computed_field
    @property
    def vision_model_base_url(self) -> Optional[str]:
        if not self.VISION_MODEL_URL:
            return None
        url = self.VISION_MODEL_URL.rstrip("/")
        if not url.endswith("/v1"):
            url = f"{url}/v1"
        return url


settings = Settings()
