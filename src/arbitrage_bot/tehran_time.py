from __future__ import annotations

from datetime import timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_tehran_cached: tzinfo | None = None


def tehran_tz() -> tzinfo:
    """Asia/Tehran با tzdata؛ بدون آن UTC+۳:۳۰ ثابت (ویندوز)."""

    global _tehran_cached
    if _tehran_cached is not None:
        return _tehran_cached
    try:
        _tehran_cached = ZoneInfo("Asia/Tehran")
    except ZoneInfoNotFoundError:
        _tehran_cached = timezone(timedelta(hours=3, minutes=30))
    return _tehran_cached
