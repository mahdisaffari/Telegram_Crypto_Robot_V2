from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(slots=True)
class ExchangeQuote:
    """
    قیمت‌ها به تومان؛ مقدار Decimal بدون تبدیل به float.

    - buy_toman: مبلغی که کاربر برای خرید یک واحد ارز از صرافی می‌پردازد (حداقل قیمت فروشنده / ask).
    - sell_toman: مبلغی که کاربر بابت فروش یک واحد ارز به صرافی دریافت می‌کند (حداکثر قیمت خریدار / bid).
    """

    exchange_key: str
    label_fa: str
    buy_toman: Decimal | None
    sell_toman: Decimal | None
    quoted_at_utc: datetime | None = None


def quote_mid_toman(q: ExchangeQuote) -> Decimal | None:
    """میانگین خرید/فروش در صورت وجود هر دو؛ در غیر این صورت همان مقدار موجود."""

    if q.buy_toman is not None and q.sell_toman is not None:
        return (q.buy_toman + q.sell_toman) / Decimal(2)
    if q.buy_toman is not None:
        return q.buy_toman
    return q.sell_toman
