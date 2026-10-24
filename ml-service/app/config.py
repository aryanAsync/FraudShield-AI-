from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory for the ml-service
BASE_DIR = Path(__file__).resolve().parent.parent

# Standard feature order expected by all models
EXPECTED_FEATURE_ORDER: list[str] = ["Time"] + [f"V{i}" for i in range(1, 29)] + ["Amount"]
TARGET_COLUMN: str = "Class"


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: str = Field(default="development", description="Environment mode")
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/fraudshield",
        description="PostgreSQL connection string using psycopg 3 driver",
    )

    # Authentication & Security
    JWT_SECRET_KEY: str = Field(
        default="dev-insecure-jwt-secret-key-change-in-production-abcdef123456",
        description="Secret key used for signing JWT access tokens",
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="Algorithm used for signing JWT")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60, description="Access token expiration window in minutes"
    )
    CORS_ORIGINS: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ],
        description="Permitted CORS origins for frontend application",
    )

    DATASET_PATH: str = Field(
        default="data/raw/creditcard.csv",
        description="Path to raw creditcard transaction dataset",
    )
    MODEL_ARTIFACT_PATH: str = Field(
        default="artifacts/fraud_model_v1.joblib",
        description="Path to serialized model artifact",
    )
    MODEL_VERSION: str = Field(
        default="fraud-model-v1",
        description="Identifier for active model version",
    )

    DECISION_THRESHOLD_OVERRIDE: float | None = Field(
        default=None,
        description="Optional manual override for decision threshold (0.0 - 1.0)",
    )
    MAX_BATCH_SIZE: int = Field(
        default=500,
        description="Maximum number of transactions allowed in a single batch inference request",
    )
    ENABLE_SHAP_EXPLANATIONS: bool = Field(
        default=True,
        description="Whether to enable SHAP feature attribution explanations",
    )

    # Risk category boundaries (scores 0-100)
    LOW_RISK_MAX: float = Field(default=30.0, description="Upper score bound for LOW risk")
    MEDIUM_RISK_MAX: float = Field(default=70.0, description="Upper score bound for MEDIUM risk")

    @field_validator("DECISION_THRESHOLD_OVERRIDE", mode="before")
    @classmethod
    def parse_empty_str_to_none(cls, v: Any) -> float | None:
        if v == "" or v is None:
            return None
        val = float(v)
        if not (0.0 <= val <= 1.0):
            raise ValueError("DECISION_THRESHOLD_OVERRIDE must be between 0.0 and 1.0")
        return val

    def resolve_dataset_path(self) -> Path:
        """Resolve dataset path checking multiple potential relative and absolute locations."""
        candidates = [
            Path(self.DATASET_PATH),
            BASE_DIR / self.DATASET_PATH,
            BASE_DIR.parent / self.DATASET_PATH,
            BASE_DIR / "data" / "raw" / "creditcard.csv",
            BASE_DIR.parent / "data" / "raw" / "creditcard.csv",
        ]
        for p in candidates:
            if p.is_file():
                return p.resolve()
        # Default fallback to candidate under base dir
        return (BASE_DIR / self.DATASET_PATH).resolve()

    def resolve_artifact_path(self) -> Path:
        """Resolve model artifact path checking relative to base dir or absolute."""
        p = Path(self.MODEL_ARTIFACT_PATH)
        if p.is_absolute():
            return p
        # Check relative to BASE_DIR first
        if (BASE_DIR / p).exists():
            return (BASE_DIR / p).resolve()
        return (BASE_DIR / p).resolve()

    def get_safe_database_url(self) -> str:
        """Return database URL with password masked for safe logging."""
        from urllib.parse import urlsplit, urlunsplit

        try:
            parts = urlsplit(self.DATABASE_URL)
            if parts.password:
                netloc = f"{parts.username}:*****@{parts.hostname}"
                if parts.port:
                    netloc += f":{parts.port}"
                return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
            return self.DATABASE_URL
        except Exception:
            return "postgresql+psycopg://***"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()


settings = get_settings()
