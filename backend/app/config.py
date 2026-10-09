from pathlib import Path
from typing import List, Union
import json
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "CodeGuard Backend"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Frontend configuration
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    # Nebius Token Factory & NVIDIA Nemotron Models
    NEBIUS_TOKEN_FACTORY_API_KEY: str = ""
    NEBIUS_TOKEN_FACTORY_BASE_URL: str = "https://api.tokenfactory.nebius.com/v1/"
    NEMOTRON_ULTRA_MODEL_ID: str = "nvidia/Nemotron-3-Ultra-550b-a55b"
    NEMOTRON_NANO_MODEL_ID: str = "nvidia/Nemotron-3_5-Lightning"
    NEMOTRON_FAST_MODEL_ID: str = "nvidia/Nemotron-3_5-Lightning"
    ULTRA_MAX_CALLS_PER_SCAN: int = 10
    ULTRA_BUDGET_USD_PER_SCAN: float = 0.05
    ULTRA_ENABLED: bool = True
    DIAGNOSIS_TOP_N: int = 15
    FIX_GENERATION_MODEL: str = "ultra"
    FIX_MIN_SEVERITY: str = "medium"

    # Nebius AI Cloud Sandbox Configuration (ConTree)
    NEBIUS_SANDBOX_API_KEY: str = ""
    NEBIUS_SANDBOX_BASE_URL: str = "https://api.studio.nebius.com/sandboxes"
    NEBIUS_SANDBOX_PROJECT_ID: str = ""
    NEBIUS_SANDBOX_DEFAULT_IMAGE: str = "node:20"
    SANDBOX_TIMEOUT_SECONDS: int = 120
    SANDBOX_MAX_CONCURRENT: int = 3
    NPM_INSTALL_TIMEOUT_SECONDS: int = 180

    # Tavily Web Search Grounding Configuration
    TAVILY_API_KEY: str = ""
    TAVILY_ENABLED: bool = True
    TAVILY_MAX_SEARCHES_PER_SCAN: int = 12

    # GitHub Integration
    GITHUB_TOKEN: str = ""

    # CORS
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "https://codeguard.dhanushkumar.in",
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

    @property
    def allowed_origins(self) -> List[str]:
        origins = list(self.CORS_ORIGINS) if isinstance(self.CORS_ORIGINS, list) else [self.CORS_ORIGINS]
        if self.FRONTEND_ORIGIN and self.FRONTEND_ORIGIN not in origins:
            origins.append(self.FRONTEND_ORIGIN)
        # Guarantee local development origins remain accessible for hybrid local/cloud testing
        for dev_origin in ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]:
            if dev_origin not in origins:
                origins.append(dev_origin)
        return origins

    model_config = SettingsConfigDict(
        env_file=(str(BASE_DIR / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
