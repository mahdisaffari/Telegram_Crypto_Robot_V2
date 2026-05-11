from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone, tzinfo
from decimal import Decimal
from html import escape
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from arbitrage_bot.exchange_clients import sort_quotes_for_display
from arbitrage_bot.formatting import format_price_digits_rounded
from arbitrage_bot.locale_fa import UNAVAILABLE
from arbitrage_bot.models import ExchangeQuote, quote_mid_toman

_tehran_cached: tzinfo | None = None


def _tehran_tz() -> tzinfo:
    """Asia/Tehran اگر tzdata نصب باشد؛ روی ویندوز بدون tzdata از UTC+۳:۳۰ ثابت استفاده می‌شود."""

    global _tehran_cached
    if _tehran_cached is not None:
        return _tehran_cached
    try:
        _tehran_cached = ZoneInfo("Asia/Tehran")
    except ZoneInfoNotFoundError:
        _tehran_cached = timezone(timedelta(hours=3, minutes=30))
    return _tehran_cached


def _sep() -> str:
    return escape("──────────────────────────")


def _today_tehran_ymd() -> str:
    return datetime.now(_tehran_tz()).strftime("%Y-%m-%d")


def _quote_time_tehran_label(quoted_at_utc: datetime | None) -> str:
    if quoted_at_utc is None:
        return escape(UNAVAILABLE)
    dt = quoted_at_utc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    local = dt.astimezone(_tehran_tz())
    return escape(local.strftime("%H:%M:%S"))


def _line_price(label_fa: str, value: Decimal | None) -> str:
    if value is None:
        return f"   <b>{escape(label_fa)}</b>: <i>{escape(UNAVAILABLE)}</i>"
    num = format_price_digits_rounded(value)
    return f"   <b>{escape(label_fa)}</b>: <code>{escape(num)}</code> تومان"


def build_price_report_html(coin: str, quotes: list[ExchangeQuote]) -> str:
    """
    گزارش خوانا برای تلگرام (HTML): بخش‌بندی، قیمت در <code>، متن فارسی منظم.
    """
    ordered = sort_quotes_for_display(quotes)
    coin_e = escape(coin)
    date_e = escape(_today_tehran_ymd())

    parts: list[str] = [
        _sep(),
        f"<b>📊  گزارش قیمت · {coin_e}</b>",
        f"<i>تاریخ امروز (تهران): {date_e}</i>",
        _sep(),
        "",
        f"<b>1) قیمت در صرافی‌ها</b>",
        "",
    ]

    for q in ordered:
        name = escape(q.label_fa)
        parts.append(f"•  <b>{name}</b>")
        if q.buy_toman is None and q.sell_toman is None:
            parts.append(f"   <i>{escape(UNAVAILABLE)}</i>")
        else:
            parts.append(
                _line_price("خرید (مبلغ پرداختی شما به ازای یک واحد)", q.buy_toman)
            )
            parts.append(
                _line_price("فروش (مبلغ دریافتی شما به ازای یک واحد)", q.sell_toman)
            )
            parts.append(
                "   <b>زمان دریافت قیمت از API (تهران)</b>: "
                f"<code>{_quote_time_tehran_label(q.quoted_at_utc)}</code>"
            )
        parts.append("")

    while parts and parts[-1] == "":
        parts.pop()

    buy_ok = [q for q in ordered if q.buy_toman is not None]
    sell_ok = [q for q in ordered if q.sell_toman is not None]
    best_buy = min(buy_ok, key=lambda q: q.buy_toman) if buy_ok else None
    best_sell = max(sell_ok, key=lambda q: q.sell_toman) if sell_ok else None

    parts.append("")
    parts.append(_sep())
    parts.append("<b>2) بهترین صرافی از نظر قیمت</b>")
    parts.append("")
    if best_buy is not None and best_buy.buy_toman is not None:
        p = format_price_digits_rounded(best_buy.buy_toman)
        parts.append(
            "•  <b>مناسب‌تر برای خرید</b> (کمترین مبلغ پرداختی به ازای یک واحد):"
        )
        parts.append(
            f"   <b>{escape(best_buy.label_fa)}</b> — "
            f"<code>{escape(p)}</code> تومان"
        )
    else:
        parts.append(
            f"•  <b>مناسب‌تر برای خرید</b>: <i>{escape(UNAVAILABLE)}</i>"
        )
    parts.append("")
    if best_sell is not None and best_sell.sell_toman is not None:
        p = format_price_digits_rounded(best_sell.sell_toman)
        parts.append(
            "•  <b>مناسب‌تر برای فروش</b> (بیشترین مبلغ دریافتی به ازای یک واحد):"
        )
        parts.append(
            f"   <b>{escape(best_sell.label_fa)}</b> — "
            f"<code>{escape(p)}</code> تومان"
        )
    else:
        parts.append(
            f"•  <b>مناسب‌تر برای فروش</b>: <i>{escape(UNAVAILABLE)}</i>"
        )

    valid = [q for q in ordered if quote_mid_toman(q) is not None]
    parts.append("")
    if len(valid) < 2:
        parts.append(
            "⚠️  <i>برای مقایسهٔ معنادار بین صرافی‌ها، حداقل به <b>دو</b> منبع با قیمت معتبر نیاز دارید.</i>"
        )

    parts.append("")
    parts.append(_sep())
    parts.append("<b>3) یادآوری</b>")
    parts.append("")
    parts.append(
        "<i>این اعداد فقط برای مقایسهٔ سریع هستند؛ کارمزد، اسپرد و "
        "امکان جابه‌جایی بین صرافی‌ها را جداگانه در نظر بگیرید.</i>"
    )
    parts.append(
        "<i>اگر جایی «خطا» است، API آن صرافی موقتاً در دسترس نبوده یا دادهٔ کافی برنگشته است.</i>"
    )
    parts.append("")
    parts.append(
        "💡  <i>برای راهنمای کامل نحوهٔ استفاده، محدودیت درخواست و فهرست ارزها، "
        "دستور</i> <b>/help</b> <i>را بفرستید.</i>"
    )

    return "\n".join(parts)
