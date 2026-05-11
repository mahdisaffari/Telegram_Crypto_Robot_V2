from __future__ import annotations

from datetime import datetime

import jdatetime

from arbitrage_bot.locale_fa import FA_DIGITS
from arbitrage_bot.tehran_time import tehran_tz

_WEEKDAYS_FA: tuple[str, ...] = (
    "شنبه",
    "یکشنبه",
    "دوشنبه",
    "سه‌شنبه",
    "چهارشنبه",
    "پنج‌شنبه",
    "جمعه",
)

_MONTHS_FA: tuple[str, ...] = (
    "فروردین",
    "اردیبهشت",
    "خرداد",
    "تیر",
    "مرداد",
    "شهریور",
    "مهر",
    "آبان",
    "آذر",
    "دی",
    "بهمن",
    "اسفند",
)


def format_today_shamsi_tehran() -> str:
    """
    تاریخ امروز به شمسی، به وقت تهران؛ متن کاملاً فارسی با ارقام فارسی.
    مثال: «دوشنبه، ۲۱ اردیبهشت ۱۴۰۵»
    """

    now = datetime.now(tehran_tz())
    jd = jdatetime.date.fromgregorian(date=now.date())
    weekday = _WEEKDAYS_FA[jd.weekday()]
    month = _MONTHS_FA[jd.month - 1]
    line = f"{weekday}، {jd.day} {month} {jd.year}"
    return line.translate(FA_DIGITS)
