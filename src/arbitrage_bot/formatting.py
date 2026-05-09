from __future__ import annotations


def format_price_en(value: float) -> str:
    """اعداد انگلیسی، جداکننده هزارگان، گرد به دو رقم اعشار."""
    rounded = round(float(value) + 1e-12, 2)
    return f"{rounded:,.2f}"
