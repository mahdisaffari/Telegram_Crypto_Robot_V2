from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True)
class ExchangeQuote:
    """قیمت نرمال‌شده به تومان برای مقایسه؛ مقدار Decimal بدون تبدیل به float."""

    exchange_key: str
    label_fa: str
    price_toman: Decimal | None
