from __future__ import annotations

import logging
import re

import aiohttp

from arbitrage_bot.config import HTTP_HEADERS

logger = logging.getLogger(__name__)

BROWSER_HEADERS: dict[str, str] = {
    **HTTP_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
}


async def _get_text(
    session: aiohttp.ClientSession, url: str, timeout_s: int
) -> str | None:
    try:
        async with session.get(
            url,
            headers=BROWSER_HEADERS,
            timeout=aiohttp.ClientTimeout(total=timeout_s),
        ) as resp:
            resp.raise_for_status()
            return await resp.text(errors="replace")
    except Exception as exc:  # noqa: BLE001
        logger.debug("HTML fetch failed %s: %s", url, exc)
        return None


def _mid(a: float, b: float) -> float:
    return (a + b) / 2.0


def _nobitex_chunk(html: str, coin: str) -> float | None:
    needle = f'"{coin.upper()}IRT"'
    pos = 0
    while True:
        i = html.find(needle, pos)
        if i < 0:
            return None
        window = html[i : i + 15000]
        m = re.search(r'"lastTradePrice"\s*:\s*"(\d+)"', window)
        if m:
            return float(m.group(1)) / 10.0
        mb = re.search(r'"bids"\s*:\s*\[\s*\[\s*"(\d+)"', window)
        ma = re.search(r'"asks"\s*:\s*\[\s*\[\s*"(\d+)"', window)
        if mb and ma:
            return _mid(float(mb.group(1)), float(ma.group(1))) / 10.0
        pos = i + len(needle)


async def scrape_nobitex_toman(
    session: aiohttp.ClientSession, coin: str, timeout_s: int
) -> float | None:
    for url in (
        "https://nobitex.ir/",
        f"https://nobitex.ir/markets/{coin.lower()}-irt",
        "https://nobitex.ir/markets",
    ):
        text = await _get_text(session, url, timeout_s)
        if not text:
            continue
        p = _nobitex_chunk(text, coin)
        if p is not None and p > 0:
            return p
    return None


def _bitpin_in_html(html: str, coin: str) -> float | None:
    sym = f"{coin.upper()}_IRT"
    for pat in (
        rf'"symbol"\s*:\s*"{re.escape(sym)}"[^}}]{{0,4000}}?"price"\s*:\s*"([\d.]+)"',
        rf'"symbol"\s*:\s*"{re.escape(sym)}"[^}}]{{0,4000}}?"price"\s*:\s*([\d.]+)',
    ):
        m = re.search(pat, html, re.I | re.DOTALL)
        if m:
            try:
                return float(m.group(1)) / 10.0
            except ValueError:
                pass
    return None


async def scrape_bitpin_toman(
    session: aiohttp.ClientSession, coin: str, timeout_s: int
) -> float | None:
    for url in (
        "https://bitpin.ir/",
        "https://bitpin.ir/markets",
        f"https://bitpin.ir/market/{coin.lower()}-irt",
    ):
        text = await _get_text(session, url, timeout_s)
        if not text:
            continue
        p = _bitpin_in_html(text, coin)
        if p is not None and p > 0:
            return p
    return None


def _ramzinex_in_html(html: str, coin: str) -> float | None:
    slug = f"{coin.lower()}irr"
    i = html.lower().find(slug)
    if i >= 0:
        window = html[i : i + 8000]
        mb = re.search(r'"buy"\s*:\s*([\d.]+)', window)
        ms = re.search(r'"sell"\s*:\s*([\d.]+)', window)
        if mb and ms:
            try:
                return _mid(float(mb.group(1)), float(ms.group(1))) / 10.0
            except ValueError:
                pass
    for pat in (
        rf'"{re.escape(coin.lower())}irr"[^\[]{{0,2000}}\[[^\]]*\][^\[]*\[[^\]]*"buy"\s*:\s*([\d.]+)',
    ):
        m = re.search(pat, html, re.I | re.DOTALL)
        if m:
            try:
                return float(m.group(1)) / 10.0
            except ValueError:
                pass
    return None


async def scrape_ramzinex_toman(
    session: aiohttp.ClientSession, coin: str, timeout_s: int
) -> float | None:
    for url in (
        "https://ramzinex.com/exchange/pt/markets",
        "https://ramzinex.com/exchange/pt",
        "https://ramzinex.com/",
    ):
        text = await _get_text(session, url, timeout_s)
        if not text:
            continue
        p = _ramzinex_in_html(text, coin)
        if p is not None and p > 0:
            return p
    return None


def _exir_in_html(html: str, coin: str) -> float | None:
    sym = f"{coin.lower()}-irt"
    i = html.find(sym)
    if i >= 0:
        window = html[i : i + 6000]
        m = re.search(r'"last"\s*:\s*([\d.]+)', window)
        if m:
            try:
                return float(m.group(1)) / 10.0
            except ValueError:
                pass
        mb = re.search(r'"bid"\s*:\s*([\d.]+)', window)
        ma = re.search(r'"ask"\s*:\s*([\d.]+)', window)
        if mb and ma:
            try:
                return _mid(float(mb.group(1)), float(ma.group(1))) / 10.0
            except ValueError:
                pass
    return None


async def scrape_exir_toman(
    session: aiohttp.ClientSession, coin: str, timeout_s: int
) -> float | None:
    for url in (
        f"https://exir.io/trade/{coin.lower()}-irt",
        "https://exir.io/",
        "https://pro.exir.io/",
    ):
        text = await _get_text(session, url, timeout_s)
        if not text:
            continue
        p = _exir_in_html(text, coin)
        if p is not None and p > 0:
            return p
    return None


def _wallex_in_html(html: str, coin: str) -> float | None:
    sym = f"{coin.upper()}TMN"
    needle = f'"{sym}"'
    pos = 0
    while True:
        i = html.find(needle, pos)
        if i < 0:
            break
        window = html[i : i + 12000]
        m = re.search(r'"lastPrice"\s*:\s*"([\d.]+)"', window)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
        mb = re.search(r'"bidPrice"\s*:\s*"([\d.]+)"', window)
        ma = re.search(r'"askPrice"\s*:\s*"([\d.]+)"', window)
        if mb and ma:
            try:
                return _mid(float(mb.group(1)), float(ma.group(1)))
            except ValueError:
                pass
        pos = i + len(needle)
    return None


async def scrape_wallex_toman(
    session: aiohttp.ClientSession, coin: str, timeout_s: int
) -> float | None:
    for url in (
        f"https://wallex.ir/coin/{coin.upper()}",
        "https://wallex.ir/markets",
        "https://wallex.ir/",
    ):
        text = await _get_text(session, url, timeout_s)
        if not text:
            continue
        p = _wallex_in_html(text, coin)
        if p is not None and p > 0:
            return p
    return None


def _sarrafex_in_html(html: str, coin: str) -> float | None:
    c = coin.upper()
    for pat in (
        rf'"counterAssetId"\s*:\s*"{re.escape(c)}"[^}}]{{0,4000}}?"latestRate"\s*:\s*([\d.]+)',
        rf'"counterAssetId"\s*:\s*"{re.escape(c)}"[^}}]{{0,4000}}?"close"\s*:\s*([\d.]+)',
    ):
        m = re.search(pat, html, re.I | re.DOTALL)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
    i = html.find(f'"counterAssetId":"{c}"')
    if i >= 0:
        window = html[i : i + 6000]
        m = re.search(r'"latestRate"\s*:\s*([\d.]+)', window)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
    return None


async def scrape_sarrafex_toman(
    session: aiohttp.ClientSession, coin: str, timeout_s: int
) -> float | None:
    for url in (
        "https://sarrafex.com/",
        "https://sarrafex.com/markets",
    ):
        text = await _get_text(session, url, timeout_s)
        if not text:
            continue
        p = _sarrafex_in_html(text, coin)
        if p is not None and p > 0:
            return p
    return None
