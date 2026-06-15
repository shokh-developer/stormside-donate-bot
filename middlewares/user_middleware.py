"""
middlewares/user_middleware.py – auto-register users on every update.
"""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from db import repository as repo

logger = logging.getLogger(__name__)


class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user:
            try:
                db_user = await repo.upsert_user(
                    telegram_id=user.id,
                    username=user.username,
                    full_name=user.full_name,
                )
                data["db_user"] = db_user
            except Exception:
                logger.exception("UserMiddleware: failed to upsert user %s", user.id)
                data["db_user"] = None

        return await handler(event, data)
