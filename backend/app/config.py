from typing import List, Union
import json
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "CodeGuard Backend"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Nebius Token Factory & NVIDIA Nemotron Models
    NEBIUS_TOKEN_FACTORY_API_KEY: str = ""
    NEBIUS_SANDBOX_API_KEY: str = ""
    NEMOTRON_ULTRA_MODEL_ID: str = "nvidia/nemotron-4-340b-instruct"
    NEMOTRON_NANO_MODEL_ID: str = "nvidia/nemotron-mini-4b-instruct"

    # CORS
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
