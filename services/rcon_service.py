"""
services/rcon_service.py – async-safe RCON client for Minecraft.

Uses mcrcon under the hood but wraps it in asyncio.to_thread so the
blocking socket call never stalls the event loop.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional, Tuple

from mcrcon import MCRcon, MCRconException

from config import config

logger = logging.getLogger(__name__)


class RCONService:
    """Stateless RCON helper.  Creates a new connection per command."""

    def __init__(self) -> None:
        self.host = config.rcon_host
        self.port = config.rcon_port
        self.password = config.rcon_password.strip()

    # ── Internal blocking helper (runs in thread pool) ──────────────────────

    def _send_blocking(self, command: str) -> str:
        # Added timeout to prevent thread stalling
        with MCRcon(
            self.host, 
            self.password, 
            port=self.port, 
            timeout=15
        ) as client:
            return client.command(command)

    # ── Public async API ─────────────────────────────────────────────────────

    async def send_command(self, command: str) -> Tuple[bool, str]:
        """
        Send *command* to the Minecraft server.

        Returns (success, response_or_error_message).
        """
        logger.info("RCON ▶ %s", command)
        try:
            response = await asyncio.to_thread(self._send_blocking, command)
            logger.info("RCON ◀ %s", response)
            return True, response
        except MCRconException as exc:
            logger.error("RCON error: %s", exc)
            return False, f"RCON error: {exc}"
        except ConnectionRefusedError:
            logger.error("RCON: connection refused (%s:%s)", self.host, self.port)
            return False, "Server offline or RCON port blocked."
        except TimeoutError:
            logger.error("RCON: timeout")
            return False, "Connection timed out."
        except Exception as exc:  # noqa: BLE001
            logger.exception("RCON unexpected error")
            return False, f"Unexpected error: {exc}"

    # ── Domain helpers ────────────────────────────────────────────────────────

    async def give_rank(self, nickname: str, lp_group: str) -> Tuple[bool, str]:
        cmd = f"lp user {nickname} parent add {lp_group}"
        return await self.send_command(cmd)

    async def give_coins(self, nickname: str, amount: int) -> Tuple[bool, str]:
        # Adjust command to your economy plugin (e.g. EssentialsX, PlayerPoints)
        cmd = f"eco give {nickname} {amount}"
        return await self.send_command(cmd)

    async def kill_player(self, nickname: str) -> Tuple[bool, str]:
        cmd = f"kill {nickname}"
        return await self.send_command(cmd)

    async def announce(self, message: str) -> Tuple[bool, str]:
        # 'broadcast' o'rniga 'say' ishlatamiz, chunki u standart buyruq.
        # Agar serveringizda EssentialsX bo'lsa, 'broadcast' ham ishlashi kerak edi.
        cmd = f'say {message}'
        return await self.send_command(cmd)

    async def is_online(self) -> bool:
        ok, _ = await self.send_command("list")
        return ok

    async def get_player_clan(self, nickname: str) -> str:
        """O'yinchining klanini aniqlash (SimpleClans yoki ClansLite uchun)."""
        # Ko'p klan pluginlari uchun /clan player [nick] ishlaydi
        ok, response = await self.send_command(f"clan player {nickname}")
        if not ok or "not found" in response.lower() or "no clan" in response.lower():
            return "Mavjud emas"
        # Bu yerda response'dan klan nomini ajratib olish logikasi (regex) bo'lishi mumkin
        # Hozircha oddiyroq ko'rinishda:
        return "Topilmadi" # Placeholder

    async def get_player_rank(self, nickname: str) -> str:
        """LuckPerms orqali o'yinchining asosiy guruhini aniqlash."""
        ok, response = await self.send_command(f"lp user {nickname} parent info")
        if ok:
            # LuckPerms response'dan 'Parent Groups:' qismini topamiz
            import re
            match = re.search(r"Parent Groups:\s*\n\s*-\s*(\w+)", response)
            if match:
                return match.group(1).capitalize()
        return "Default"


# Singleton
rcon = RCONService()
