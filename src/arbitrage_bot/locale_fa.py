from __future__ import annotations

from arbitrage_bot.coins import SUPPORTED_COINS

FA_DIGITS = str.maketrans("0123456789,.-", "۰۱۲۳۴۵۶۷۸۹،٫-")

EXCHANGE_LABELS_FA: dict[str, str] = {
    "nobitex": "نوبیتکس",
    "bitpin": "بیت‌پین",
    "ramzinex": "رمزینکس",
    "exir": "اکسیر",
    "wallex": "والکس",
    "sarrafex": "صرافکس",
    "tabdeal": "تبدیل",
    "abantether": "آبان‌تتر",
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
    coins_line = " | ".join(sorted(SUPPORTED_COINS))
    return (
        " ** سلام و درود ** \n\n"
        "این ربات قیمت رمز ارز مورد نظر را در لحظه (به تومان) نمایش میدهد.\n\n"
        "* چطور استفاده کنم؟ \n\n"
        "1) نماد ارز را به انگلیسی بفرستید (مثلاً SOL)\n\n"
        "2) گزارشی که دریافت میکنید شامل قیمت هر صرافی، شکاف آربیتراژ و بهترین صرافی برای خرید/فروش است.\n\n"
        f"* ارزهای فعلی * : \n\n{coins_line}\n\n"
        "راهنما با دستور : /help "
    )


UNAVAILABLE: str = " خطا در گرفتن قیمت از api !"
