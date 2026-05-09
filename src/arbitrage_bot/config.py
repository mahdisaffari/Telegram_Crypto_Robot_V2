from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_pkg_dir = Path(__file__).resolve().parent
_project_root = _pkg_dir.parent.parent
# ریشهٔ پروژه و مسیر قدیمی داخل پکیج (هر دو)
load_dotenv(_project_root / ".env")
load_dotenv(_pkg_dir / ".env")
load_dotenv()


SUPPORTED_COINS: frozenset[str] = frozenset({"USDT", "USDC", "DAI", "BTC", "ETH", "TRX"})

DEFAULT_REQUEST_TIMEOUT_S: int = 14

HTTP_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    request_timeout_s: int = DEFAULT_REQUEST_TIMEOUT_S
    """شناسهٔ فایل استیکر تلگرام (اختیاری). از @userinfobot یا reply به استیکر."""
    report_sticker_file_id: str | None = None


def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "BOT_TOKEN is missing. Copy .env.example to .env and set BOT_TOKEN."
        )
    sticker = os.getenv("STICKER_FILE_ID", "").strip() or os.getenv(
        "REPORT_STICKER_FILE_ID", ""
    ).strip()
    return Settings(
        bot_token=token,
        report_sticker_file_id=sticker or None,
    )
