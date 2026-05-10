from __future__ import annotations

import logging

import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from arbitrage_bot.coins import format_coin_title, resolve_exchange_coin, user_coin_supported
from arbitrage_bot.config import HTTP_HEADERS, Settings
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

    if not user_coin_supported(raw):
        await message.answer(unsupported_coin_message(raw))
        return

    coin_api = resolve_exchange_coin(raw)

    wait = await message.answer(
        "⏳  در حال گرفتن قیمت از صرافی‌ها…\n"
        "معمولا چند ثانیه زمان میبرد."
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
    except Exception:
        logger.exception("Failed building report for %s", coin_api)
        try:
            await wait.edit_text(
                "** 500 Error **.\n"
                "Pleas trying again after 20 secound."
            )
        except Exception:
            await message.answer(
                "** 500 Error **\n"
                "Pleas trying again after 20 secound."
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
