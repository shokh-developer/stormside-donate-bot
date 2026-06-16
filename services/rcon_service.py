"""
services/rcon_service.py – async RCON client for Minecraft.

Uses aio-mc-rcon (pip: aio-mc-rcon, import: aiomcrcon) v3.4.2.
Pure asyncio — no signal-based timeouts, safe inside aiogram handlers.
"""
from __future__ import annotations

import logging
import re
from typing import Tuple

from aiomcrcon import Client, IncorrectPasswordError, RCONConnectionError, ClientNotConnectedError

from config import config

logger = logging.getLogger(__name__)

_CONNECT_TIMEOUT = 3.0
_CMD_TIMEOUT = 3.0


class RCONService:
    """Stateless async RCON helper. Opens a fresh connection per command."""

    def __init__(self) -> None:
        self.host = config.rcon_host
        self.port = config.rcon_port
        self.password = config.rcon_password.strip()

    async def _run(self, command: str) -> str:
        client = Client(self.host, self.port, self.password)
        try:
            await client.connect(timeout=_CONNECT_TIMEOUT)
            response, _ = await client.send_cmd(command, timeout=_CMD_TIMEOUT)
            return response
        finally:
            await client.close()

    async def send_command(self, command: str) -> Tuple[bool, str]:
        logger.info("RCON ▶ %s", command)
        try:
            response = await self._run(command)
            logger.info("RCON ◀ %s", response)
            return True, response
        except IncorrectPasswordError:
            logger.error("RCON: authentication failed")
            return False, "RCON authentication failed – check RCON_PASSWORD."
        except RCONConnectionError as exc:
            logger.error("RCON: connection error: %s", exc)
            return False, f"Connection error: {exc}"
        except ClientNotConnectedError:
            logger.error("RCON: client not connected")
            return False, "RCON client not connected."
        except Exception as exc:
            logger.exception("RCON unexpected error")
            return False, f"Unexpected error: {exc}"

    async def give_rank(self, nickname: str, lp_group: str) -> Tuple[bool, str]:
        return await self.send_command(f"lp user {nickname} parent add {lp_group}")

    async def give_coins(self, nickname: str, amount: int) -> Tuple[bool, str]:
        return await self.send_command(f"eco give {nickname} {amount}")

    async def kill_player(self, nickname: str) -> Tuple[bool, str]:
        return await self.send_command(f"kill {nickname}")

    async def announce(self, message: str) -> Tuple[bool, str]:
        return await self.send_command(f"say {message}")

    async def is_online(self) -> bool:
        ok, _ = await self.send_command("list")
        return ok

    async def get_player_rank(self, nickname: str) -> str:
        ok, response = await self.send_command(f"lp user {nickname} parent info")
        if ok:
            match = re.search(r"Parent Groups:\s*\n\s*-\s*(\w+)", response)
            if match:
                return match.group(1).capitalize()
        return "Default"


# Singleton
rcon = RCONService()
