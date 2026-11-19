"""Application configuration loaded from environment variables."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    google_api_key: str
    gemini_model: str


def get_settings() -> Settings:
    """Read the current environment configuration.

    Reading is deferred so environment variables changed in tests or at runtime
    are reflected without restarting the Python process.
    """
    load_dotenv(PROJECT_ROOT / ".env")
    return Settings(
        google_api_key=os.getenv("GOOGLE_API_KEY", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "").strip(),
    )
