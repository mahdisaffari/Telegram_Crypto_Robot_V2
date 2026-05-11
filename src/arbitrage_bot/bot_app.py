from __future__ import annotations

import logging
from html import escape

import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from arbitrage_bot.coins import format_coin_title, resolve_exchange_coin, user_coin_supported
from arbitrage_bot.config import HTTP_HEADERS, Settings
from arbitrage_bot.exchange_clients import gather_exchange_quotes
from arbitrage_bot.locale_fa import FA_DIGITS, help_message_html, unsupported_coin_message_html
from arbitrage_bot.price_rate_limit import (
    cooldown_seconds_display,
    quote_cooldown_remaining_s,
    record_quote_request,
)
from arbitrage_bot.middlewares import SessionMiddleware, SettingsMiddleware
from arbitrage_bot.reports import build_price_report_html

logger = logging.getLogger(__name__)

router = Router()


@router.message(CommandStart())
@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(help_message_html(), parse_mode=ParseMode.HTML)


@router.message(F.text)
async def handle_coin_query(message: Message, http_session: aiohttp.ClientSession, settings: Settings) -> None:
    raw = (message.text or "").strip()
    if raw.startswith("/"):
        await message.answer(
            "<b>⚠️ این دستور ثبت نشده است.</b>\n\n"
            "برای دیدن قیمت، فقط <b>نماد ارز</b> (مثل <code>BTC</code>) را بفرستید.\n"
            "راهنما: <b>/help</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    if not user_coin_supported(raw):
        await message.answer(
            unsupported_coin_message_html(raw),
            parse_mode=ParseMode.HTML,
        )
        return

    coin_api = resolve_exchange_coin(raw)

    uid = message.from_user.id if message.from_user else 0
    cooldown_left = await quote_cooldown_remaining_s(uid, coin_api)
    if cooldown_left is not None:
        wait_s = cooldown_seconds_display(cooldown_left)
        wait_fa = str(wait_s).translate(FA_DIGITS)
        await message.answer(
            "<b>⏱ کمی صبر کنید</b>\n\n"
            "برای هر ارز، حداکثر <b>یک بار در هر دقیقه</b> می‌توانید گزارش قیمت بگیرید.\n\n"
            f"حدود <b>{escape(wait_fa)}</b> ثانیهٔ دیگر دوباره امتحان کنید.\n\n"
            "<i>توضیح بیشتر:</i> /help",
            parse_mode=ParseMode.HTML,
        )
        return

    wait = await message.answer(
        "<b>⏳ در حال آماده‌سازی گزارش…</b>\n\n"
        "در حال گرفتن قیمت از چند صرافی هستم.\n"
        "<i>معمولاً چند ثانیه طول می‌کشد.</i>",
        parse_mode=ParseMode.HTML,
    )
    try:
        quotes = await gather_exchange_quotes(http_session, coin_api, settings.request_timeout_s)
        report_html = build_price_report_html(format_coin_title(raw), quotes)
        try:
            await wait.delete()
        except Exception:
            pass
        if settings.report_sticker_file_id:
            try:
                await message.answer_sticker(settings.report_sticker_file_id)
            except Exception as sticker_exc:
                logger.warning("Could not send sticker: %s", sticker_exc)
        await message.answer(report_html, parse_mode=ParseMode.HTML)
        await record_quote_request(uid, coin_api)
    except Exception:
        logger.exception("Failed building report for %s", coin_api)
        try:
            await wait.edit_text(
                "<b>❌ خطای موقت</b>\n\n"
                "گزارش ساخته نشد. لطفاً چند لحظه دیگر دوباره همان نماد را بفرستید.\n"
                "<i>اگر تکرار شد، /help را ببینید یا بعداً امتحان کنید.</i>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            await message.answer(
                "<b>❌ خطای موقت</b>\n\n"
                "گزارش ساخته نشد. لطفاً کمی بعد دوباره تلاش کنید.\n"
                "<i>راهنما:</i> /help",
                parse_mode=ParseMode.HTML,
            )


def build_dispatcher(settings: Settings, session: aiohttp.ClientSession) -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(router)
    dp.update.middleware(SessionMiddleware(session))
    dp.update.middleware(SettingsMiddleware(settings))
    return dp


async def run_bot(settings: Settings) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    bot = Bot(settings.bot_token)
    async with aiohttp.ClientSession(headers=HTTP_HEADERS) as session:
        dp = build_dispatcher(settings, session)
        await dp.start_polling(bot)
