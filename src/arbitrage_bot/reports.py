from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from html import escape

from arbitrage_bot.exchange_clients import sort_quotes_for_display
from arbitrage_bot.formatting import format_price_digits_rounded
from arbitrage_bot.locale_fa import FA_DIGITS, UNAVAILABLE
from arbitrage_bot.models import ExchangeQuote, quote_mid_toman
from arbitrage_bot.persian_calendar import format_today_shamsi_tehran
from arbitrage_bot.tehran_time import tehran_tz


def _to_fa_digits(s: str) -> str:
    return s.translate(FA_DIGITS)


def _sep() -> str:
    return escape("━━━━━━━━━━━━━━━━━━━━━━━━━━")


def _quote_time_tehran_label(quoted_at_utc: datetime | None) -> str:
    if quoted_at_utc is None:
        return escape(UNAVAILABLE)
    dt = quoted_at_utc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    local = dt.astimezone(tehran_tz())
    return escape(_to_fa_digits(local.strftime("%H:%M:%S")))


def _line_price(icon: str, label_fa: str, value: Decimal | None) -> str:
    if value is None:
        return (
            f"   {icon} <b>{escape(label_fa)}</b>\n"
            f"      <i>{escape(UNAVAILABLE)}</i>"
        )
    num = format_price_digits_rounded(value)
    return (
        f"   {icon} <b>{escape(label_fa)}</b>\n"
        f"      <code>{escape(num)}</code> <i>تومان</i>"
    )


def build_price_report_html(coin: str, quotes: list[ExchangeQuote]) -> str:
    """
    گزارش تلگرام (HTML): بلوک‌های خوانا، تاریخ شمسی، زمان با ارقام فارسی.
    """
    ordered = sort_quotes_for_display(quotes)
    coin_e = escape(coin)
    date_line = escape(format_today_shamsi_tehran())

    parts: list[str] = [
        _sep(),
        f"<b>📈 گزارش لحظه‌ای · {coin_e}</b>",
        f"📅 <b>امروز</b>\n<code>{date_line}</code>",
        _sep(),
        "",
        "<b>۱ · قیمت صرافی‌ها</b>",
        "<i>خرید= مبلغی که می‌پردازید | فروش= مبلغی که دریافت می‌کنید</i>",
        "",
    ]

    for q in ordered:
        name = escape(q.label_fa)
        parts.append(f"🏦 <b>{name}</b>")
        if q.buy_toman is None and q.sell_toman is None:
            parts.append(f"   <i>{escape(UNAVAILABLE)}</i>")
        else:
            parts.append(
                _line_price("🛒", "خرید (هر واحد ارز)", q.buy_toman)
            )
            parts.append(
                _line_price("💵", "فروش (هر واحد ارز)", q.sell_toman)
            )
            parts.append(
                "   🕐 <b>زمان گرفتن قیمت</b>\n"
                f"      <code>{_quote_time_tehran_label(q.quoted_at_utc)}</code>"
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
    parts.append("<b>۲ · پیشنهاد بر اساس قیمت</b>")
    parts.append("")
    if best_buy is not None and best_buy.buy_toman is not None:
        p = format_price_digits_rounded(best_buy.buy_toman)
        parts.append("✅ <b>ارزان‌ترین خرید برای شما</b>")
        parts.append(
            f"   صرافی <b>{escape(best_buy.label_fa)}</b>\n"
            f"   با حدود <code>{escape(p)}</code> <i>تومان به ازای هر واحد</i>"
        )
    else:
        parts.append(f"✅ <b>ارزان‌ترین خرید</b>\n   <i>{escape(UNAVAILABLE)}</i>")
    parts.append("")
    if best_sell is not None and best_sell.sell_toman is not None:
        p = format_price_digits_rounded(best_sell.sell_toman)
        parts.append("✅ <b>بیشترین دریافت از فروش برای شما</b>")
        parts.append(
            f"   صرافی <b>{escape(best_sell.label_fa)}</b>\n"
            f"   با حدود <code>{escape(p)}</code> <i>تومان به ازای هر واحد</i>"
        )
    else:
        parts.append(f"✅ <b>بیشترین دریافت از فروش</b>\n   <i>{escape(UNAVAILABLE)}</i>")

    valid = [q for q in ordered if quote_mid_toman(q) is not None]
    parts.append("")
    if len(valid) < 2:
        parts.append(
            "⚠️ <i>برای مقایسهٔ دقیق‌تر، حداقل دو صرافی باید قیمت معتبر برگردانند.</i>"
        )

    parts.append("")
    parts.append(_sep())
    parts.append("<b>۳ · یادآوری</b>")
    parts.append("")
    parts.append(
        "• اعداد <b>تقریبی و مقایسه‌ای</b> هستند؛ کارمزد، اسپرد و نقدشوندگی را "
        "حتماً در خود صرافی بررسی کنید."
    )
    parts.append(
        "• اگر جایی «در دسترس نیست» دیدید، یعنی آن لحظه API پاسخ نداده یا داده ناقص بوده است."
    )
    parts.append("")
    parts.append(
        "💬 راهنمای کامل، محدودیت زمانی و فهرست ارزها:\n"
        "   <b>/help</b>"
    )

    return "\n".join(parts)
