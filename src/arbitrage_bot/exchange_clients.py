from __future__ import annotations

import asyncio
import logging
from decimal import Decimal
from typing import Any

import aiohttp

from arbitrage_bot.config import HTTP_HEADERS
from arbitrage_bot.html_scrapers import (
    scrape_bitpin_toman,
    scrape_exir_toman,
    scrape_nobitex_toman,
    scrape_ramzinex_toman,
    scrape_sarrafex_toman,
    scrape_wallex_toman,
)
from arbitrage_bot.locale_fa import EXCHANGE_LABELS_FA
from arbitrage_bot.models import ExchangeQuote

logger = logging.getLogger(__name__)


def _d(x: Any) -> Decimal:
    return Decimal(str(x))


def _mid_d(bid: Decimal, ask: Decimal) -> Decimal:
    return (bid + ask) / Decimal(2)


def _irt_pair_mid_to_toman(raw_mid: Decimal) -> Decimal:
    """تاب‌دیال/آبان برای جفت‌های IRT: مقادیر بزرگ را از ریال به تومان (÷۱۰) یکسان می‌کند."""

    if raw_mid >= Decimal("1000000"):
        return raw_mid / Decimal(10)
    return raw_mid


def _depth_best_mid(book: dict[str, Any]) -> Decimal | None:
    bids = book.get("bids") or []
    asks = book.get("asks") or []
    if not bids or not asks:
        return None
    b0, a0 = bids[0], asks[0]
    bid_p = _d(b0[0]) if isinstance(b0, (list, tuple)) else _d(b0)
    ask_p = _d(a0[0]) if isinstance(a0, (list, tuple)) else _d(a0)
    return _mid_d(bid_p, ask_p)


async def fetch_nobitex(session: aiohttp.ClientSession, coin: str, timeout_s: int) -> ExchangeQuote:
    label = EXCHANGE_LABELS_FA["nobitex"]
    url = f"https://apiv2.nobitex.ir/v3/orderbook/{coin}IRT"
    price_toman: Decimal | None = None
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout_s)) as resp:
            resp.raise_for_status()
            data: dict[str, Any] = await resp.json(content_type=None)
        key = f"{coin}IRT"
        ob: dict[str, Any] | None = None
        nested = data.get(key)
        if isinstance(nested, dict):
            ob = nested
        elif isinstance(data.get("asks"), list) and isinstance(data.get("bids"), list):
            ob = data
        if isinstance(ob, dict):
            asks = ob.get("asks") or []
            bids = ob.get("bids") or []
            last_tp = ob.get("lastTradePrice")
            price_irr: Decimal | None = None
            if asks and bids:
                price_irr = _mid_d(_d(bids[0][0]), _d(asks[0][0]))
            if last_tp is not None and price_irr is None:
                price_irr = _d(last_tp)
            if price_irr is not None:
                price_toman = price_irr / Decimal(10)
    except Exception as exc:  # noqa: BLE001 — ایزوله برای هر صرافی
        logger.debug("Nobitex API failure: %s", exc)
    if price_toman is None:
        try:
            price_toman = await scrape_nobitex_toman(session, coin, timeout_s)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Nobitex HTML scrape failure: %s", exc)
    return ExchangeQuote("nobitex", label, price_toman)


async def fetch_bitpin(session: aiohttp.ClientSession, coin: str, timeout_s: int) -> ExchangeQuote:
    label = EXCHANGE_LABELS_FA["bitpin"]
    url = "https://api.bitpin.market/api/v1/mkt/tickers/"
    target = f"{coin}_IRT"
    price_toman: Decimal | None = None
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout_s)) as resp:
            resp.raise_for_status()
            payload: Any = await resp.json(content_type=None)
        rows: list[Any]
        if isinstance(payload, dict):
            rows = payload.get("results") or payload.get("data") or []
        else:
            rows = payload if isinstance(payload, list) else []
        chosen: dict[str, Any] | None = None
        for row in rows:
            if not isinstance(row, dict):
                continue
            sym = str(row.get("symbol", "")).upper()
            if sym == target.upper():
                chosen = row
                break
        if isinstance(chosen, dict):
            raw_price = (
                chosen.get("price")
                or chosen.get("last_price")
                or chosen.get("lastPrice")
                or chosen.get("latest")
            )
            if raw_price is not None:
                price_toman = _d(raw_price) / Decimal(10)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Bitpin API failure: %s", exc)
    if price_toman is None:
        try:
            price_toman = await scrape_bitpin_toman(session, coin, timeout_s)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Bitpin HTML scrape failure: %s", exc)
    return ExchangeQuote("bitpin", label, price_toman)


def _ramzinex_currency_en(raw: Any) -> str:
    if isinstance(raw, dict):
        return str(raw.get("en") or "").strip().upper()
    return ""


def _ramzinex_pair_matches(coin: str, m: dict[str, Any]) -> bool:
    c = coin.upper()
    ts = m.get("tv_symbol")
    if isinstance(ts, dict):
        tv = str(ts.get("ramzinex") or "").lower().replace("_", "")
        if tv in (f"{coin.lower()}irr", f"{coin.lower()}irt"):
            return True
    base = _ramzinex_currency_en(m.get("base_currency_symbol"))
    quote = _ramzinex_currency_en(m.get("quote_currency_symbol"))
    if base == c and quote in ("IRR", "IRT"):
        return True
    # بعضی پاسخ‌ها فیلد پایه/نقل را خالی برمی‌گردانند؛ از نام مسیر استفاده می‌کنیم
    un = str(m.get("url_name") or "").lower()
    slug = c.lower()
    if un.startswith(f"{slug}-") or un.startswith(f"{slug}_"):
        if "irr" in un or "irt" in un or "rial" in un:
            return True
    return False


def _ramzinex_buy_sell(m: dict[str, Any]) -> tuple[Decimal | None, Decimal | None]:
    buy_raw = m.get("buy")
    sell_raw = m.get("sell")
    fin = m.get("financial")
    if isinstance(fin, dict):
        buy_raw = buy_raw if buy_raw is not None else fin.get("buy")
        sell_raw = sell_raw if sell_raw is not None else fin.get("sell")
        ins = fin.get("instant") or fin.get("market") or fin.get("last")
        if isinstance(ins, dict):
            buy_raw = buy_raw if buy_raw is not None else ins.get("buy")
            sell_raw = sell_raw if sell_raw is not None else ins.get("sell")
    try:
        if buy_raw is None or sell_raw is None:
            return None, None
        return _d(buy_raw), _d(sell_raw)
    except Exception:
        return None, None


async def fetch_ramzinex(session: aiohttp.ClientSession, coin: str, timeout_s: int) -> ExchangeQuote:
    label = EXCHANGE_LABELS_FA["ramzinex"]
    urls = (
        "https://publicapi.ramzinex.com/exchange/api/v1.0/exchange/pairs",
        "https://ramzinex.com/exchange/api/v1.0/exchange/pairs",
    )
    last_err: Exception | None = None
    for url in urls:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout_s)) as resp:
                resp.raise_for_status()
                data: dict[str, Any] = await resp.json(content_type=None)
            markets = data.get("data")
            if not isinstance(markets, list):
                continue
            match: dict[str, Any] | None = None
            for m in markets:
                if isinstance(m, dict) and _ramzinex_pair_matches(coin, m):
                    match = m
                    break
            if match is None:
                continue
            buy, sell = _ramzinex_buy_sell(match)
            if buy is None or sell is None:
                continue
            irr_mid = _mid_d(buy, sell)
            return ExchangeQuote("ramzinex", label, irr_mid / Decimal(10))
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            logger.debug("Ramzinex attempt %s failed: %s", url, exc)
            continue
    if last_err:
        logger.debug("Ramzinex all API endpoints failed: %s", last_err)
    try:
        scraped = await scrape_ramzinex_toman(session, coin, timeout_s)
        if scraped is not None:
            return ExchangeQuote("ramzinex", label, scraped)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Ramzinex HTML scrape failure: %s", exc)
    return ExchangeQuote("ramzinex", label, None)


async def _wallex_depth_mid(session: aiohttp.ClientSession, coin: str, timeout_s: int) -> Decimal | None:
    sym = f"{coin.upper()}TMN"
    url = f"https://api.wallex.ir/v1/depth?symbol={sym}"
    wall_headers = {
        **HTTP_HEADERS,
        "Origin": "https://wallex.ir",
        "Referer": "https://wallex.ir/",
    }
    try:
        async with session.get(
            url, headers=wall_headers, timeout=aiohttp.ClientTimeout(total=timeout_s)
        ) as resp:
            resp.raise_for_status()
            data: dict[str, Any] = await resp.json(content_type=None)
        if data.get("success") is False:
            return None
        result = data.get("result") or {}
        if not isinstance(result, dict):
            return None
        book: dict[str, Any] | None = result.get(sym) if isinstance(result.get(sym), dict) else None
        if book is None:
            for k, v in result.items():
                if str(k).upper() == sym.upper() and isinstance(v, dict):
                    book = v
                    break
        if book is None or not isinstance(book, dict):
            return None
        bids = book.get("bid") or []
        asks = book.get("ask") or []
        if not bids or not asks:
            return None
        b0, a0 = bids[0], asks[0]
        if isinstance(b0, dict):
            bid_p = _d(b0.get("price", 0))
        else:
            bid_p = _d(b0[0])
        if isinstance(a0, dict):
            ask_p = _d(a0.get("price", 0))
        else:
            ask_p = _d(a0[0])
        return _mid_d(bid_p, ask_p)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Wallex depth fallback: %s", exc)
        return None


def _wallex_resolve_market(symbols_map: dict[str, Any], want: str) -> dict[str, Any] | None:
    if want in symbols_map and isinstance(symbols_map[want], dict):
        return symbols_map[want]
    wu = want.upper()
    for k, mkt in symbols_map.items():
        if str(k).upper() == wu and isinstance(mkt, dict):
            return mkt
    for _k, mkt in symbols_map.items():
        if not isinstance(mkt, dict):
            continue
        if str(mkt.get("symbol") or "").upper() == wu:
            return mkt
    return None


async def fetch_exir(session: aiohttp.ClientSession, coin: str, timeout_s: int) -> ExchangeQuote:
    label = EXCHANGE_LABELS_FA["exir"]
    symbol = f"{coin.lower()}-irt"
    url = f"https://api.exir.io/v2/ticker?symbol={symbol}"
    price_toman: Decimal | None = None
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout_s)) as resp:
            if resp.status == 404:
                pass
            else:
                resp.raise_for_status()
                t: dict[str, Any] = await resp.json(content_type=None)
                last = t.get("last")
                bid = t.get("bid")
                ask = t.get("ask")
                price_irr: Decimal | None = None
                if bid is not None and ask is not None:
                    price_irr = _mid_d(_d(bid), _d(ask))
                elif last is not None:
                    price_irr = _d(last)
                if price_irr is not None:
                    price_toman = price_irr / Decimal(10)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Exir API failure: %s", exc)
    if price_toman is None:
        try:
            price_toman = await scrape_exir_toman(session, coin, timeout_s)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Exir HTML scrape failure: %s", exc)
    return ExchangeQuote("exir", label, price_toman)


async def fetch_wallex(session: aiohttp.ClientSession, coin: str, timeout_s: int) -> ExchangeQuote:
    label = EXCHANGE_LABELS_FA["wallex"]
    symbol = f"{coin.upper()}TMN"
    url = "https://api.wallex.ir/v1/markets"
    wall_headers = {
        **HTTP_HEADERS,
        "Origin": "https://wallex.ir",
        "Referer": "https://wallex.ir/",
    }
    try:
        async with session.get(
            url, headers=wall_headers, timeout=aiohttp.ClientTimeout(total=timeout_s)
        ) as resp:
            resp.raise_for_status()
            data: dict[str, Any] = await resp.json(content_type=None)
        price: Decimal | None = None
        if data.get("success") is not False:
            res = data.get("result") or {}
            symbols_map = res.get("symbols")
            if isinstance(symbols_map, dict):
                mkt = _wallex_resolve_market(symbols_map, symbol)
                if isinstance(mkt, dict):
                    stats = mkt.get("stats") or {}
                    bid = stats.get("bidPrice")
                    ask = stats.get("askPrice")
                    last = stats.get("lastPrice")
                    if bid is not None and ask is not None:
                        price = _mid_d(_d(bid), _d(ask))
                    elif last is not None:
                        price = _d(last)
        if price is None:
            price = await _wallex_depth_mid(session, coin, timeout_s)
        if price is None:
            try:
                price = await scrape_wallex_toman(session, coin, timeout_s)
            except Exception as se:  # noqa: BLE001
                logger.debug("Wallex HTML scrape (after API): %s", se)
        if price is None:
            return ExchangeQuote("wallex", label, None)
        # نمادهای TMN از قبل به تومان هستند.
        return ExchangeQuote("wallex", label, price)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Wallex API failure: %s", exc)
        depth_price = await _wallex_depth_mid(session, coin, timeout_s)
        if depth_price is not None:
            return ExchangeQuote("wallex", label, depth_price)
        try:
            scraped = await scrape_wallex_toman(session, coin, timeout_s)
            if scraped is not None:
                return ExchangeQuote("wallex", label, scraped)
        except Exception as se:  # noqa: BLE001
            logger.debug("Wallex HTML scrape failure: %s", se)
        return ExchangeQuote("wallex", label, None)


async def fetch_tabdeal(session: aiohttp.ClientSession, coin: str, timeout_s: int) -> ExchangeQuote:
    """قیمت از API عمومی تبدیل (مانند بایننس): عمق بازار IRT — docs.tabdeal.org"""
    label = EXCHANGE_LABELS_FA["tabdeal"]
    bases = [coin.upper()]
    if coin.upper() == "MATIC":
        bases = ["MATIC", "POL"]
    price_toman: Decimal | None = None
    for base in bases:
        symbol = f"{base.upper()}IRT"
        url = f"https://api1.tabdeal.org/r/api/v1/depth?symbol={symbol}&limit=10"
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout_s)) as resp:
                if resp.status == 404:
                    continue
                resp.raise_for_status()
                data: dict[str, Any] = await resp.json(content_type=None)
            mid_raw = _depth_best_mid(data)
            if mid_raw is not None:
                price_toman = _irt_pair_mid_to_toman(mid_raw)
                break
        except Exception as exc:  # noqa: BLE001
            logger.debug("Tabdeal API failure %s: %s", symbol, exc)
    return ExchangeQuote("tabdeal", label, price_toman)


async def fetch_abantether(session: aiohttp.ClientSession, coin: str, timeout_s: int) -> ExchangeQuote:
    """خرید/فروش OTC از api.abantether.com — docs.abantether.com"""
    label = EXCHANGE_LABELS_FA["abantether"]
    url = "https://api.abantether.com/api/v1/manager/otc/ticker"
    keys_try = [f"{coin.upper()}IRT"]
    if coin.upper() == "MATIC":
        keys_try = ["MATICIRT", "POLIRT"]
    price_toman: Decimal | None = None
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout_s)) as resp:
            resp.raise_for_status()
            payload: dict[str, Any] = await resp.json(content_type=None)
        markets = payload.get("data")
        if isinstance(markets, dict):
            markets = markets.get("markets")
        if not isinstance(markets, dict):
            return ExchangeQuote("abantether", label, None)
        row: dict[str, Any] | None = None
        for key in keys_try:
            r = markets.get(key)
            if isinstance(r, dict):
                row = r
                break
        if not isinstance(row, dict):
            return ExchangeQuote("abantether", label, None)
        if row.get("active") is False:
            return ExchangeQuote("abantether", label, None)
        buy_raw = row.get("buy_price")
        sell_raw = row.get("sell_price")
        if buy_raw is None or sell_raw is None:
            return ExchangeQuote("abantether", label, None)
        mid_raw = _mid_d(_d(buy_raw), _d(sell_raw))
        price_toman = _irt_pair_mid_to_toman(mid_raw)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Aban Tether API failure: %s", exc)
    return ExchangeQuote("abantether", label, price_toman)


async def fetch_sarrafex(session: aiohttp.ClientSession, coin: str, timeout_s: int) -> ExchangeQuote:
    label = EXCHANGE_LABELS_FA["sarrafex"]
    url = "https://sarrafex.com/api/gateway/exchanger/query/market"
    price_toman: Decimal | None = None
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout_s)) as resp:
            resp.raise_for_status()
            data: dict[str, Any] = await resp.json(content_type=None)
        rows = data.get("value")
        if isinstance(rows, list):
            chosen: dict[str, Any] | None = None
            for row in rows:
                if not isinstance(row, dict):
                    continue
                base_id = str(row.get("baseAssetId", "")).upper()
                counter_id = str(row.get("counterAssetId", "")).upper()
                if counter_id == coin.upper() and base_id == "IRT":
                    chosen = row
                    break
            if isinstance(chosen, dict):
                rate = chosen.get("latestRate") or chosen.get("close")
                if rate is not None:
                    price_toman = _d(rate)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Sarrafex API failure: %s", exc)
    if price_toman is None:
        try:
            price_toman = await scrape_sarrafex_toman(session, coin, timeout_s)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Sarrafex HTML scrape failure: %s", exc)
    return ExchangeQuote("sarrafex", label, price_toman)


async def gather_exchange_quotes(
    session: aiohttp.ClientSession, coin: str, timeout_s: int
) -> list[ExchangeQuote]:
    """هم‌زمان از همه صرافی‌ها قیمت می‌گیرد؛ خطای هر صرافی جداگانه مصون می‌ماند."""

    tasks = (
        fetch_nobitex(session, coin, timeout_s),
        fetch_bitpin(session, coin, timeout_s),
        fetch_ramzinex(session, coin, timeout_s),
        fetch_exir(session, coin, timeout_s),
        fetch_wallex(session, coin, timeout_s),
        fetch_sarrafex(session, coin, timeout_s),
        fetch_tabdeal(session, coin, timeout_s),
        fetch_abantether(session, coin, timeout_s),
    )
    return list(await asyncio.gather(*tasks))


def sort_quotes_for_display(quotes: list[ExchangeQuote]) -> list[ExchangeQuote]:
    order = [
        "nobitex",
        "bitpin",
        "ramzinex",
        "exir",
        "wallex",
        "sarrafex",
        "tabdeal",
        "abantether",
    ]
    rank = {k: i for i, k in enumerate(order)}
    return sorted(quotes, key=lambda q: rank.get(q.exchange_key, 99))
