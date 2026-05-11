from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import aiohttp

from arbitrage_bot.config import HTTP_HEADERS
from arbitrage_bot.locale_fa import EXCHANGE_LABELS_FA
from arbitrage_bot.models import ExchangeQuote

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _d(x: Any) -> Decimal:
    return Decimal(str(x))


def _mid_d(bid: Decimal, ask: Decimal) -> Decimal:
    return (bid + ask) / Decimal(2)


def _irt_pair_mid_to_toman(raw_mid: Decimal) -> Decimal:
    """تاب‌دیال/آبان برای جفت‌های IRT: مقادیر بزرگ را از ریال به تومان (÷۱۰) یکسان می‌کند."""

    if raw_mid >= Decimal("1000000"):
        return raw_mid / Decimal(10)
    return raw_mid


def _irt_leg_to_toman(raw: Decimal) -> Decimal:
    return _irt_pair_mid_to_toman(raw)


def _depth_best_bid_ask(book: dict[str, Any]) -> tuple[Decimal | None, Decimal | None]:
    bids = book.get("bids") or []
    asks = book.get("asks") or []
    if not bids or not asks:
        return None, None
    b0, a0 = bids[0], asks[0]
    bid_p = _d(b0[0]) if isinstance(b0, (list, tuple)) else _d(b0)
    ask_p = _d(a0[0]) if isinstance(a0, (list, tuple)) else _d(a0)
    return bid_p, ask_p


def _depth_best_mid(book: dict[str, Any]) -> Decimal | None:
    bid_p, ask_p = _depth_best_bid_ask(book)
    if bid_p is None or ask_p is None:
        return None
    return _mid_d(bid_p, ask_p)


def _quote(
    exchange_key: str,
    label: str,
    buy_toman: Decimal | None,
    sell_toman: Decimal | None,
    quoted_at: datetime | None,
) -> ExchangeQuote:
    return ExchangeQuote(exchange_key, label, buy_toman, sell_toman, quoted_at)


async def fetch_nobitex(session: aiohttp.ClientSession, coin: str, timeout_s: int) -> ExchangeQuote:
    label = EXCHANGE_LABELS_FA["nobitex"]
    url = f"https://apiv2.nobitex.ir/v3/orderbook/{coin}IRT"
    buy_toman: Decimal | None = None
    sell_toman: Decimal | None = None
    quoted_at: datetime | None = None
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
            if asks and bids:
                quoted_at = _utc_now()
                ask_irr = _d(asks[0][0])
                bid_irr = _d(bids[0][0])
                buy_toman = ask_irr / Decimal(10)
                sell_toman = bid_irr / Decimal(10)
            elif last_tp is not None:
                quoted_at = _utc_now()
                last = _d(last_tp) / Decimal(10)
                buy_toman = last
                sell_toman = last
    except Exception as exc:  # noqa: BLE001 — ایزوله برای هر صرافی
        logger.debug("Nobitex API failure: %s", exc)
    return _quote("nobitex", label, buy_toman, sell_toman, quoted_at)


def _bitpin_row_bid_ask(chosen: dict[str, Any]) -> tuple[Decimal | None, Decimal | None]:
    def to_toman_pair(bid_raw: Any, ask_raw: Any) -> tuple[Decimal | None, Decimal | None]:
        if bid_raw is None or ask_raw is None:
            return None, None
        try:
            return _d(bid_raw) / Decimal(10), _d(ask_raw) / Decimal(10)
        except Exception:
            return None, None

    for bk, ak in (
        ("bid", "ask"),
        ("best_bid", "best_ask"),
        ("bestBid", "bestAsk"),
        ("highest_bid", "lowest_ask"),
    ):
        if chosen.get(bk) is not None and chosen.get(ak) is not None:
            return to_toman_pair(chosen.get(bk), chosen.get(ak))
    if chosen.get("buy") is not None and chosen.get("sell") is not None:
        return to_toman_pair(chosen.get("buy"), chosen.get("sell"))
    return None, None


async def fetch_bitpin(session: aiohttp.ClientSession, coin: str, timeout_s: int) -> ExchangeQuote:
    label = EXCHANGE_LABELS_FA["bitpin"]
    url = "https://api.bitpin.market/api/v1/mkt/tickers/"
    target = f"{coin}_IRT"
    buy_toman: Decimal | None = None
    sell_toman: Decimal | None = None
    quoted_at: datetime | None = None
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
            bid_t, ask_t = _bitpin_row_bid_ask(chosen)
            if bid_t is not None and ask_t is not None:
                quoted_at = _utc_now()
                sell_toman = bid_t
                buy_toman = ask_t
            else:
                raw_price = (
                    chosen.get("price")
                    or chosen.get("last_price")
                    or chosen.get("lastPrice")
                    or chosen.get("latest")
                )
                if raw_price is not None:
                    quoted_at = _utc_now()
                    mid = _d(raw_price) / Decimal(10)
                    buy_toman = mid
                    sell_toman = mid
    except Exception as exc:  # noqa: BLE001
        logger.debug("Bitpin API failure: %s", exc)
    return _quote("bitpin", label, buy_toman, sell_toman, quoted_at)


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
            api_buy, api_sell = _ramzinex_buy_sell(match)
            if api_buy is None or api_sell is None:
                continue
            # api_buy: نرخ خرید صرافی از کاربر (کاربر می‌فروشد)؛ api_sell: نرخ فروش صرافی به کاربر (کاربر می‌خرد)
            quoted_at = _utc_now()
            sell_toman = api_buy / Decimal(10)
            buy_toman = api_sell / Decimal(10)
            return _quote("ramzinex", label, buy_toman, sell_toman, quoted_at)
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            logger.debug("Ramzinex attempt %s failed: %s", url, exc)
            continue
    if last_err:
        logger.debug("Ramzinex all API endpoints failed: %s", last_err)
    return _quote("ramzinex", label, None, None, None)


async def _wallex_depth_bid_ask(
    session: aiohttp.ClientSession, coin: str, timeout_s: int
) -> tuple[Decimal | None, Decimal | None]:
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
            return None, None
        result = data.get("result") or {}
        if not isinstance(result, dict):
            return None, None
        book: dict[str, Any] | None = result.get(sym) if isinstance(result.get(sym), dict) else None
        if book is None:
            for k, v in result.items():
                if str(k).upper() == sym.upper() and isinstance(v, dict):
                    book = v
                    break
        if book is None or not isinstance(book, dict):
            return None, None
        bids = book.get("bid") or []
        asks = book.get("ask") or []
        if not bids or not asks:
            return None, None
        b0, a0 = bids[0], asks[0]
        if isinstance(b0, dict):
            bid_p = _d(b0.get("price", 0))
        else:
            bid_p = _d(b0[0])
        if isinstance(a0, dict):
            ask_p = _d(a0.get("price", 0))
        else:
            ask_p = _d(a0[0])
        return bid_p, ask_p
    except Exception as exc:  # noqa: BLE001
        logger.debug("Wallex depth fallback: %s", exc)
        return None, None


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
    buy_toman: Decimal | None = None
    sell_toman: Decimal | None = None
    quoted_at: datetime | None = None
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
                if bid is not None and ask is not None:
                    quoted_at = _utc_now()
                    sell_toman = _d(bid) / Decimal(10)
                    buy_toman = _d(ask) / Decimal(10)
                elif last is not None:
                    quoted_at = _utc_now()
                    mid = _d(last) / Decimal(10)
                    buy_toman = mid
                    sell_toman = mid
    except Exception as exc:  # noqa: BLE001
        logger.debug("Exir API failure: %s", exc)
    return _quote("exir", label, buy_toman, sell_toman, quoted_at)


async def fetch_wallex(session: aiohttp.ClientSession, coin: str, timeout_s: int) -> ExchangeQuote:
    label = EXCHANGE_LABELS_FA["wallex"]
    symbol = f"{coin.upper()}TMN"
    url = "https://api.wallex.ir/v1/markets"
    wall_headers = {
        **HTTP_HEADERS,
        "Origin": "https://wallex.ir",
        "Referer": "https://wallex.ir/",
    }
    buy_toman: Decimal | None = None
    sell_toman: Decimal | None = None
    quoted_at: datetime | None = None
    try:
        async with session.get(
            url, headers=wall_headers, timeout=aiohttp.ClientTimeout(total=timeout_s)
        ) as resp:
            resp.raise_for_status()
            data: dict[str, Any] = await resp.json(content_type=None)
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
                        quoted_at = _utc_now()
                        sell_toman = _d(bid)
                        buy_toman = _d(ask)
                    elif last is not None:
                        quoted_at = _utc_now()
                        mid = _d(last)
                        buy_toman = mid
                        sell_toman = mid
        if buy_toman is None or sell_toman is None:
            bd, ak = await _wallex_depth_bid_ask(session, coin, timeout_s)
            if bd is not None and ak is not None:
                quoted_at = _utc_now()
                sell_toman = bd
                buy_toman = ak
        if buy_toman is None and sell_toman is None:
            return _quote("wallex", label, None, None, None)
        return _quote("wallex", label, buy_toman, sell_toman, quoted_at)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Wallex API failure: %s", exc)
        bd, ak = await _wallex_depth_bid_ask(session, coin, timeout_s)
        if bd is not None and ak is not None:
            return _quote("wallex", label, ak, bd, _utc_now())
        return _quote("wallex", label, None, None, None)


async def fetch_tabdeal(session: aiohttp.ClientSession, coin: str, timeout_s: int) -> ExchangeQuote:
    """قیمت از API عمومی تبدیل (مانند بایننس): عمق بازار IRT — docs.tabdeal.org"""
    label = EXCHANGE_LABELS_FA["tabdeal"]
    bases = [coin.upper()]
    if coin.upper() == "MATIC":
        bases = ["MATIC", "POL"]
    buy_toman: Decimal | None = None
    sell_toman: Decimal | None = None
    quoted_at: datetime | None = None
    for base in bases:
        symbol = f"{base.upper()}IRT"
        url = f"https://api1.tabdeal.org/r/api/v1/depth?symbol={symbol}&limit=10"
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout_s)) as resp:
                if resp.status == 404:
                    continue
                resp.raise_for_status()
                data: dict[str, Any] = await resp.json(content_type=None)
            bid_raw, ask_raw = _depth_best_bid_ask(data)
            if bid_raw is not None and ask_raw is not None:
                quoted_at = _utc_now()
                sell_toman = _irt_leg_to_toman(bid_raw)
                buy_toman = _irt_leg_to_toman(ask_raw)
                break
        except Exception as exc:  # noqa: BLE001
            logger.debug("Tabdeal API failure %s: %s", symbol, exc)
    return _quote("tabdeal", label, buy_toman, sell_toman, quoted_at)


async def fetch_abantether(session: aiohttp.ClientSession, coin: str, timeout_s: int) -> ExchangeQuote:
    """خرید/فروش OTC از api.abantether.com — docs.abantether.com"""
    label = EXCHANGE_LABELS_FA["abantether"]
    url = "https://api.abantether.com/api/v1/manager/otc/ticker"
    keys_try = [f"{coin.upper()}IRT"]
    if coin.upper() == "MATIC":
        keys_try = ["MATICIRT", "POLIRT"]
    buy_toman: Decimal | None = None
    sell_toman: Decimal | None = None
    quoted_at: datetime | None = None
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout_s)) as resp:
            resp.raise_for_status()
            payload: dict[str, Any] = await resp.json(content_type=None)
        markets = payload.get("data")
        if isinstance(markets, dict):
            markets = markets.get("markets")
        if not isinstance(markets, dict):
            return _quote("abantether", label, None, None, None)
        row: dict[str, Any] | None = None
        for key in keys_try:
            r = markets.get(key)
            if isinstance(r, dict):
                row = r
                break
        if not isinstance(row, dict):
            return _quote("abantether", label, None, None, None)
        if row.get("active") is False:
            return _quote("abantether", label, None, None, None)
        buy_raw = row.get("buy_price")
        sell_raw = row.get("sell_price")
        if buy_raw is None or sell_raw is None:
            return _quote("abantether", label, None, None, None)
        quoted_at = _utc_now()
        buy_toman = _irt_leg_to_toman(_d(buy_raw))
        sell_toman = _irt_leg_to_toman(_d(sell_raw))
    except Exception as exc:  # noqa: BLE001
        logger.debug("Aban Tether API failure: %s", exc)
    return _quote("abantether", label, buy_toman, sell_toman, quoted_at)


async def fetch_sarrafex(session: aiohttp.ClientSession, coin: str, timeout_s: int) -> ExchangeQuote:
    label = EXCHANGE_LABELS_FA["sarrafex"]
    url = "https://sarrafex.com/api/gateway/exchanger/query/market"
    buy_toman: Decimal | None = None
    sell_toman: Decimal | None = None
    quoted_at: datetime | None = None
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
                    quoted_at = _utc_now()
                    p = _d(rate)
                    buy_toman = p
                    sell_toman = p
    except Exception as exc:  # noqa: BLE001
        logger.debug("Sarrafex API failure: %s", exc)
    return _quote("sarrafex", label, buy_toman, sell_toman, quoted_at)


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
