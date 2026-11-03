from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


@dataclass(slots=True)
class Settings:
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    admin_ids: list[int] = field(
        default_factory=lambda: [
            int(item.strip())
            for item in os.getenv("ADMIN_IDS", "").split(",")
            if item.strip()
        ]
    )
    default_model: str = field(default_factory=lambda: os.getenv("DEFAULT_MODEL", "llama-3.3-70b-versatile"))
    database_path: str = field(default_factory=lambda: os.getenv("DB_PATH", str(ROOT_DIR / "data" / "lumi_ai.db")))
    app_name: str = "LumiAI"


settings = Settings()


def get_db_path() -> str:
    return settings.database_path
