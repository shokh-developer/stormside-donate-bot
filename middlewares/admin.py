"""
middlewares/admin.py – middleware & decorator to restrict admin handlers.
"""
from __future__ import annotations

import logging
from functools import wraps
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from config import config

logger = logging.getLogger(__name__)


def admin_required(handler: Callable) -> Callable:
    """Decorator for handler functions that require admin access."""

    @wraps(handler)
    async def wrapper(event: Any, *args: Any, **kwargs: Any) -> Any:
        user_id: int = 0
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id if event.from_user else 0

        if not config.is_admin(user_id):
            logger.warning("Unauthorized admin access attempt by user_id=%s", user_id)
            if isinstance(event, CallbackQuery):
                await event.answer("⛔ Access denied.", show_alert=True)
            elif isinstance(event, Message):
                await event.answer("⛔ You don't have permission to do that.")
            return
        return await handler(event, *args, **kwargs)

    return wrapper
