"""
main.py – Stromeside Telegram Donation Bot entry point.
"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from db.database import init_db
from handlers import all_routers
from middlewares.user_middleware import UserMiddleware
from utils.logger import setup_logging

logger = logging.getLogger(__name__)


async def main() -> None:
    setup_logging()
    logger.info("🚀 Stromeside Bot starting up...")

    # Init database
    await init_db()

    # Setup session for proxy if configured
    session = None
    if config.proxy_url:
        session = AiohttpSession(proxy=config.proxy_url)

    # Create bot and dispatcher
    bot = Bot(
        token=config.bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Register middlewares
    dp.update.middleware(UserMiddleware())

    # Register routers
    for router in all_routers:
        dp.include_router(router)

    # Start polling
    logger.info("Bot polling started. Press Ctrl+C to stop.")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
