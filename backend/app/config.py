"""
EnergyPulse configuration — loads from environment variables with sensible defaults.
"""

from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

# Locate the .env file — check backend/ first, then project root
_backend_dir = Path(__file__).resolve().parent.parent
_project_root = _backend_dir.parent
_env_file = _backend_dir / ".env"
if not _env_file.exists():
    _env_file = _project_root / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- Groq AI ---
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # --- Gemini AI ---
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # --- Database ---
    DATABASE_URL: str = "sqlite:///energy_pulse.db"

    # --- Scheduler ---
    FETCH_INTERVAL_MINUTES: int = 60

    # --- Article retention ---
    MAX_ARTICLE_AGE_HOURS: int = 48

    # --- Embeddings ---
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    model_config = {
        "env_file": str(_env_file),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# Singleton instance used throughout the application
settings = Settings()
