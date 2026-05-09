from __future__ import annotations

from arbitrage_bot.config import SUPPORTED_COINS

FA_DIGITS = str.maketrans("0123456789,.-", "۰۱۲۳۴۵۶۷۸۹،٫-")

EXCHANGE_LABELS_FA: dict[str, str] = {
    "nobitex": "نوبیتکس",
    "bitpin": "بیت‌پین",
    "ramzinex": "رمزینکس",
    "exir": "اکسیر",
    "wallex": "والکس",
    "sarrafex": "صرافکس",
}


def fa_format_number(value: float, decimals: int = 0) -> str:
    """Format a float with grouping and Persian digits."""
    if decimals <= 0:
        text = f"{value:,.0f}"
    else:
        text = f"{value:,.{decimals}f}"
    return text.translate(FA_DIGITS)


def unsupported_coin_message(coin: str) -> str:
    listed = "، ".join(sorted(SUPPORTED_COINS))
    return (
        f"این نماد پشتیبانی نمی‌شود: {coin}\n\n"
        f"نمادهای مجاز:\n{listed}\n\n"
        "فقط حروف انگلیسی بفرستید، مثلاً:\n"
        "USDT"
    )


def help_message() -> str:
    coins_line = "، ".join(sorted(SUPPORTED_COINS))
    return (
        "سلام.\n\n"
        "این ربات قیمت چند صرافی را با هم مقایسه می‌کند و اختلاف را به تومان نشان می‌دهد.\n\n"
        "چطور استفاده کنم؟\n"
        "۱) نماد ارز را به انگلیسی بفرستید (بدون / و بدون فاصله اضافه).\n"
        "۲) گزارش شامل قیمت هر صرافی، شکاف آربیتراژ و بهترین خرید/فروش است.\n\n"
        f"ارزهای فعلی: {coins_line}\n\n"
        "مثال:\n"
        "USDT\n\n"
        "دستورها:\n"
        "/start یا /help — همین راهنما"
    )


UNAVAILABLE: str = "نامشخص/قطعی موقت"
