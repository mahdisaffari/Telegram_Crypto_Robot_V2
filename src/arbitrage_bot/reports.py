from __future__ import annotations

from html import escape

from arbitrage_bot.exchange_clients import sort_quotes_for_display
from arbitrage_bot.formatting import format_price_en
from arbitrage_bot.locale_fa import UNAVAILABLE
from arbitrage_bot.models import ExchangeQuote


def _sep() -> str:
    return escape("────────────────────────")


def build_price_report_html(coin: str, quotes: list[ExchangeQuote]) -> str:
    """
    گزارش خوانا برای تلگرام (HTML): بخش‌بندی، قیمت در <code>، متن فارسی منظم.
    """
    ordered = sort_quotes_for_display(quotes)
    coin_e = escape(coin)

    parts: list[str] = [
        _sep(),
        f"<b>📊  گزارش قیمت · {coin_e}</b>",
        _sep(),
        ""
        "",
        f"<b>۱) قیمت در صرافی‌ها</b>",
        "",
    ]

    for q in ordered:
        name = escape(q.label_fa)
        if q.price_toman is None:
            parts.append(f"•  <b>{name}</b>")
            parts.append(f"   <i>{escape(UNAVAILABLE)}</i>")
        else:
            num = format_price_en(q.price_toman)
            parts.append(f"•  <b>{name}</b>")
            parts.append(f"   <code>{escape(num)}</code>  تومان")
        parts.append("")

    while parts and parts[-1] == "":
        parts.pop()

    valid = [q for q in ordered if q.price_toman is not None]
    parts.append("")
    parts.append(_sep())
    parts.append(f"<b>۲) آربیتراژ و بهترین صرافی</b>")
    parts.append("")

    if len(valid) < 2:
        parts.append(
            "⚠️  <i>برای محاسبهٔ اختلاف قیمت، حداقل به <b>دو</b> صرافی با قیمت معتبر نیاز است.</i>"
        )
    else:
        prices = [q.price_toman for q in valid if q.price_toman is not None]
        gap = max(prices) - min(prices)
        buy_q = min(valid, key=lambda x: x.price_toman or float("inf"))
        sell_q = max(valid, key=lambda x: x.price_toman or float("-inf"))

        parts.append("شکاف قیمت (گران‌ترین منهای ارزان‌ترین):")
        parts.append(f"   <code>{escape(format_price_en(gap))}</code>  تومان")
        parts.append("")
        parts.append("ارزان‌ترین (مناسب‌تر برای <b>خرید</b>):")
        parts.append(
            f"   {escape(buy_q.label_fa)}  ←  <code>{escape(format_price_en(buy_q.price_toman or 0.0))}</code>"
        )
        parts.append("")
        parts.append("گران‌ترین (مناسب‌تر برای <b>فروش</b>):")
        parts.append(
            f"   {escape(sell_q.label_fa)}  ←  <code>{escape(format_price_en(sell_q.price_toman or 0.0))}</code>"
        )

    parts.append("")
    parts.append(_sep())
    parts.append(f"<b>۳) یادآوری</b>")
    parts.append("")
    parts.append(
        "<i>این اعداد فقط برای مقایسهٔ سریع هستند؛ کارمزد، اسپرد و "
        "امکان جابه‌جایی بین صرافی‌ها را جداگانه در نظر بگیرید.</i>"
    )
    parts.append(
        "<i>اگر جایی «خطا» است، API یا سایت آن صرافی موقتاً در دسترس نبوده است.</i>"
    )

    return "\n".join(parts)
