from __future__ import annotations

import re

"""نماد پایهٔ بازار برای API صرافی‌ها (IRT/TMN و غیره)."""

BASE_COINS: frozenset[str] = frozenset(
    {
        "USDT",
        "USDC",
        "DAI",
        "BTC",
        "ETH",
        "TRX",
        "XRP",
        "XLM",
        "LTC",
        "SOL",
        "MATIC",
    }
)

# ورودی‌های مجاز کاربر (شامل USDC با شبکه)
_USER_ALIASES_FOR_HELP: tuple[str, ...] = (
    "USDC-TRC20",
    "USDC_TRC20",
    "USDC-TRC",
    "USDC-BEP20",
    "USDC_BEP20",
    "USDC-BEP",
    "USDC-BSC",
)

SUPPORTED_COINS: frozenset[str] = frozenset(BASE_COINS | frozenset(_USER_ALIASES_FOR_HELP))


def normalize_user_input(text: str) -> str:
    """یکسان‌سازی برای مقایسهٔ مجاز بودن (حروف بزرگ، بدون فاصله اضافه)."""
    return re.sub(r"\s+", "", (text or "").strip()).upper()


def resolve_exchange_coin(user_input: str) -> str:
    """
    نماد پایه برای درخواست API (مثلاً همهٔ حالت‌های USDC شبکه‌دار → USDC).
    MATIC در صرافی‌هایی که POL استفاده می‌کنند در لایهٔ fetch جدا هندل می‌شود.
    """
    u = normalize_user_input(user_input)
    if not u:
        return ""
    u_compact = u.replace("-", "").replace("_", "")
    if u_compact.startswith("USDC") and u_compact != "USDC":
        return "USDC"
    return u_compact


def format_coin_title(user_input: str) -> str:
    """عنوان نمایش در گزارش (خط تیره به‌جای زیرخط)."""
    u = normalize_user_input(user_input)
    return u.replace("_", "-")


def user_coin_supported(user_input: str) -> bool:
    u = normalize_user_input(user_input)
    if u in SUPPORTED_COINS:
        return True
    return resolve_exchange_coin(user_input) in BASE_COINS

