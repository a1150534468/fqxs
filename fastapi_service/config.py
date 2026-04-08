from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FQXS AI Content Generation Service"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8001
    mock_generation: bool = True
    llm_api_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-3.5-turbo"
    django_api_url: str = "http://localhost:8000"
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    model_config = SettingsConfigDict(
        env_prefix="FASTAPI_",
        env_file=".env",
        case_sensitive=False,
    )


settings = Settings()
