from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ExchangeQuote:
    """Normalized quote for one venue (price always in تومان when present)."""

    exchange_key: str
    label_fa: str
    price_toman: float | None
