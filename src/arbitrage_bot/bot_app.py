from __future__ import annotations

import logging

import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from arbitrage_bot.config import HTTP_HEADERS, SUPPORTED_COINS, Settings
from arbitrage_bot.exchange_clients import gather_exchange_quotes
from arbitrage_bot.locale_fa import help_message, unsupported_coin_message
from arbitrage_bot.middlewares import SessionMiddleware, SettingsMiddleware
from arbitrage_bot.reports import build_price_report_html

logger = logging.getLogger(__name__)

router = Router()


@router.message(CommandStart())
@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(help_message())


@router.message(F.text)
async def handle_coin_query(message: Message, http_session: aiohttp.ClientSession, settings: Settings) -> None:
    raw = (message.text or "").strip()
    if raw.startswith("/"):
        await message.answer(
            "این دستور تعریف نشده است.\n"
            "برای راهنما بفرمایید:\n/help"
        )
        return

    coin = raw.upper().replace(" ", "")
    if coin not in SUPPORTED_COINS:
        await message.answer(unsupported_coin_message(raw))
        return

    wait = await message.answer(
        "⏳  در حال گرفتن قیمت از صرافی‌ها…\n"
        "معمولا چند ثانیه طول می‌کشد."
    )
    try:
        quotes = await gather_exchange_quotes(http_session, coin, settings.request_timeout_s)
        report_html = build_price_report_html(coin, quotes)
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
    except Exception:
        logger.exception("Failed building report for %s", coin)
        try:
            await wait.edit_text(
                "خطای موقت پیش آمد؛ گزارش ساخته نشد.\n"
                "یک دقیقه بعد دوباره همان نماد را بفرستید."
            )
        except Exception:
            await message.answer(
                "خطای موقت پیش آمد؛ گزارش ساخته نشد.\n"
                "یک دقیقه بعد دوباره همان نماد را بفرستید."
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
