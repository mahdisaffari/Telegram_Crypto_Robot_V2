from __future__ import annotations

from html import escape

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


UNAVAILABLE: str = "در دسترس نیست"


def unsupported_coin_message_html(user_input: str) -> str:
    coin_e = escape(user_input.strip() or "؟")
    codes = " ".join(f"<code>{escape(c)}</code>" for c in sorted(SUPPORTED_COINS))
    return (
        "<b>❌ این نماد در ربات تعریف نشده</b>\n\n"
        f"شما فرستادید: {coin_e}\n\n"
        "<b>نمادهای مجاز</b>\n"
        f"{codes}\n\n"
        "نماد را <b>فقط با حروف انگلیسی</b> بفرستید، مثلاً:\n"
        "<code>BTC</code> یا <code>USDT</code>\n\n"
        "<i>راهنما:</i> /help"
    )


def help_message_html() -> str:
    codes = " ".join(f"<code>{escape(c)}</code>" for c in sorted(SUPPORTED_COINS))
    return (
        "<b>📘 راهنمای ربات مقایسهٔ قیمت</b>\n\n"
        "با این ربات می‌توانید برای چند صرافی ایرانی، "
        "<b>قیمت خرید و فروش</b> یک ارز را <i>به تومان</i> (با نمایش رند به عدد صحیح) "
        "ببینید؛ داده از <b>API عمومی</b> صرافی‌ها گرفته می‌شود.\n\n"
        "<b>▫️ چطور استفاده کنم؟</b>\n"
        "• فقط <b>نماد ارز</b> را به انگلیسی بفرستید؛ مثلاً <code>SOL</code>\n"
        "• برای دیدن دوبارهٔ همین راهنما: <code>/help</code>\n\n"
        "<b>▫️ داخل گزارش چه هست؟</b>\n"
        "• تاریخ <b>امروز به شمسی</b> (وقت تهران)\n"
        "• برای هر صرافی: مبلغ خرید، مبلغ فروش، و زمان دریافت قیمت\n"
        "• پیشنهاد: <b>ارزان‌ترین خرید</b> و <b>بیشترین دریافت از فروش</b> بین صرافی‌هایی که پاسخ داده‌اند\n\n"
        "<b>▫️ محدودیت درخواست</b>\n"
        "برای هر کاربر و <b>هر ارز</b>، حداکثر <b>یک بار در هر ۶۰ ثانیه</b> می‌توانید گزارش قیمت بگیرید "
        "(مثلاً بعد از <code>SOL</code> یک دقیقه صبر کنید تا دوباره <code>SOL</code> بزنید؛ "
        "برای ارز دیگر، محدودیت جداست).\n\n"
        "<b>▫️ نکته مهم</b>\n"
        "اعداد برای <b>مقایسهٔ سریع</b> است؛ کارمزد، اسپرد و شرایط واقعی معامله را در خود صرافی چک کنید.\n\n"
        "<b>ارزهای پشتیبانی‌شده</b>\n"
        f"{codes}"
    )
