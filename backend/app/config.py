from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    gigachat_credentials: str = ""
    tavily_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_vision_model: str = "llava:7b"
    ollama_vision_fallback_models: str = "llava:7b,moondream:latest"
    ollama_text_model: str = "qwen2.5:7b"
    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'moodroute.db'}"
    chroma_path: str = str(BASE_DIR / "data" / "chroma")
    upload_dir: str = str(BASE_DIR / "uploads")
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
