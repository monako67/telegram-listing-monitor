from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    bot_token: str
    allowed_user_ids: frozenset[int]
    database_path: str = "data.sqlite3"
    default_interval_minutes: int = 10
    min_interval_minutes: int = 2
    max_links_per_check: int = 100
    user_agent: str = "Mozilla/5.0 (compatible; ListingMonitor/1.0)"


def _positive_int(name: str, default: int) -> int:
    value = int(os.getenv(name, default))
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def load_config() -> Config:
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("BOT_TOKEN is required")

    raw_ids = os.getenv("ALLOWED_USER_IDS", "")
    allowed_ids = frozenset(int(item.strip()) for item in raw_ids.split(",") if item.strip())
    minimum = _positive_int("MIN_INTERVAL_MINUTES", 2)
    default = _positive_int("DEFAULT_INTERVAL_MINUTES", 10)
    if default < minimum:
        raise ValueError("DEFAULT_INTERVAL_MINUTES cannot be below MIN_INTERVAL_MINUTES")

    return Config(
        bot_token=token,
        allowed_user_ids=allowed_ids,
        database_path=os.getenv("DATABASE_PATH", "data.sqlite3"),
        default_interval_minutes=default,
        min_interval_minutes=minimum,
        max_links_per_check=_positive_int("MAX_LINKS_PER_CHECK", 100),
        user_agent=os.getenv("USER_AGENT", "Mozilla/5.0 (compatible; ListingMonitor/1.0)"),
    )


