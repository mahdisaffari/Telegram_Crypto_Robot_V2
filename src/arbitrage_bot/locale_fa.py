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
        "سلام؛ به ربات مقایسهٔ قیمت خوش آمدید.\n\n"
        "این ربات برای هر ارز، قیمت خرید و فروش (به تومان، بدون اعشار در نمایش) را از چند صرافی "
        "از طریق API عمومی می‌گیرد و در یک گزارش نشان می‌دهد.\n\n"
        "چطور استفاده کنم؟\n"
        "• فقط نماد ارز را به انگلیسی بفرستید، مثلاً: BTC یا USDT\n"
        "• دستور /help همین متن را دوباره نشان می‌دهد.\n\n"
        "داخل گزارش چه می‌بینید؟\n"
        "• برای هر صرافی: مبلغی که برای خرید یک واحد می‌پردازید، مبلغی که با فروش یک واحد دریافت می‌کنید، "
        "و زمان گرفتن قیمت (به وقت تهران).\n"
        "• بخش «بهترین صرافی»: ارزان‌ترین گزینه برای خرید و گران‌ترین گزینه برای فروش (از دید شما).\n\n"
        "محدودیت درخواست\n"
        "• برای هر کاربر و هر ارز، حداکثر یک بار در هر ۶۰ ثانیه می‌توانید قیمت بگیرید "
        "(مثلاً بعد از SOL باید یک دقیقه صبر کنید تا دوباره SOL بزنید؛ ارز دیگر محدودیت جدا دارد).\n\n"
        "نکته\n"
        "• اعداد صرفاً برای مقایسهٔ سریع‌اند؛ کارمزد، نقدشوندگی و شرایط هر صرافی را جدا بررسی کنید.\n\n"
        f"ارزهای پشتیبانی‌شده:\n{coins_line}\n"
    )


UNAVAILABLE: str = " خطا در گرفتن قیمت از api !"
