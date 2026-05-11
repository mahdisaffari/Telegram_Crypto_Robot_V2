from __future__ import annotations

import asyncio
import math
from time import monotonic
from typing import Dict, Tuple

_COOLDOWN_S = 60.0
_lock = asyncio.Lock()
_last: Dict[Tuple[int, str], float] = {}


async def quote_cooldown_remaining_s(user_id: int, coin_api: str) -> float | None:
    """
    اگر برای این کاربر و این نماد API هنوز در پنجرهٔ ۶۰ ثانیه‌ای است،
    ثانیه‌های باقی‌مانده را برمی‌گرداند؛ در غیر این صورت None (مجاز به درخواست).
    """
    key = (user_id, coin_api.upper())
    async with _lock:
        prev = _last.get(key)
        if prev is None:
            return None
        elapsed = monotonic() - prev
        if elapsed >= _COOLDOWN_S:
            del _last[key]
            return None
        return max(0.0, _COOLDOWN_S - elapsed)


async def record_quote_request(user_id: int, coin_api: str) -> None:
    """بعد از ارسال موفق گزارش قیمت به کاربر فراخوانی شود."""

    async with _lock:
        _last[(user_id, coin_api.upper())] = monotonic()


def cooldown_seconds_display(remaining: float) -> int:
    return max(1, int(math.ceil(remaining)))
