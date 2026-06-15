"""
services/rcon_service.py – async RCON client for Minecraft.

Uses aiomcrcon (pure async, no signal-based timeouts) so it works safely
inside aiogram async handlers without the "signal only works in main thread"
error that mcrcon triggers when called via asyncio.to_thread.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Tuple

from aiomcrcon import Client, RCONAuthenticationError

from config import config

logger = logging.getLogger(__name__)

_TIMEOUT = 15.0  # seconds per command


class RCONService:
    """Stateless async RCON helper. Opens a fresh connection per command."""

    def __init__(self) -> None:
        self.host = config.rcon_host
        self.port = config.rcon_port
        self.password = config.rcon_password.strip()

    async def _run(self, command: str) -> str:
        async with Client(self.host, self.port, self.password) as client:
            response, _ = await client.send_cmd(command)
        return response

    async def send_command(self, command: str) -> Tuple[bool, str]:
        logger.info("RCON ▶ %s", command)
        try:
            response = await asyncio.wait_for(self._run(command), timeout=_TIMEOUT)
            logger.info("RCON ◀ %s", response)
            return True, response
        except RCONAuthenticationError:
            logger.error("RCON: authentication failed")
            return False, "RCON authentication failed – check RCON_PASSWORD."
        except ConnectionRefusedError:
            logger.error("RCON: connection refused (%s:%s)", self.host, self.port)
            return False, "Server offline or RCON port blocked."
        except asyncio.TimeoutError:
            logger.error("RCON: timed out after %ss", _TIMEOUT)
            return False, f"Connection timed out after {int(_TIMEOUT)}s."
        except OSError as exc:
            logger.error("RCON network error: %s", exc)
            return False, f"Network error: {exc}"
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
