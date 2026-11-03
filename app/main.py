from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError
from aiohttp import web

from app.config import settings
from app.database import init_db
from app.handlers import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


async def delete_webhook_with_retry(bot: Bot, attempts: int = 5) -> None:
    for attempt in range(1, attempts + 1):
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            return
        except TelegramNetworkError as exc:
            if attempt == attempts:
                raise RuntimeError(
                    "Could not connect to Telegram to prepare the bot. "
                    "Check your internet connection and try again."
                ) from exc
            delay = min(2 ** attempt, 30)
            logging.warning(
                "Telegram connection failed during startup (attempt %s/%s). "
                "Retrying in %s seconds: %s",
                attempt,
                attempts,
                delay,
                exc,
            )
            await asyncio.sleep(delay)


async def health_check(_: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def main() -> None:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN must be configured in the .env file.")

    await init_db()
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    app = web.Application()
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    try:
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", "10000")))
        await site.start()
        logging.info("Health check server listening on port %s", os.getenv("PORT", "10000"))
        await delete_webhook_with_retry(bot)
        await dp.start_polling(bot, close_bot_session=False)
    finally:
        await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
