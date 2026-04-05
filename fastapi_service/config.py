from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FQXS AI Content Generation Service"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8001
    mock_generation: bool = True
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
