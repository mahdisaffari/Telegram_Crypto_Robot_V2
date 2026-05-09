from __future__ import annotations

from decimal import Decimal


def format_price_digits_exact(value: Decimal | None) -> str:
    """
    فقط ارقام انگلیسی و در صورت نیاز یک نقطهٔ اعشار؛ بدون ویرگول یا گرد کردن به float.
    """
    if value is None:
        return ""
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    s = format(value, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "".join(c for c in s if c.isdigit() or c == ".")
