"""
config.py – centralised settings loaded from .env
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent


def _required(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"Required env variable '{key}' is missing. Check .env")
    return val


def _int_list(key: str) -> List[int]:
    raw = os.getenv(key, "")
    return [int(s) for s in raw.split(",") if s.strip().isdigit()]


@dataclass
class Config:
    # Bot
    bot_token: str = field(default_factory=lambda: _required("BOT_TOKEN"))
    admin_ids: List[int] = field(default_factory=lambda: _int_list("ADMIN_IDS"))
    admin_chat_id: int = field(
        default_factory=lambda: int(os.getenv("ADMIN_CHAT_ID") or "0")
if (os.getenv("ADMIN_CHAT_ID") or "0").lstrip("-").isdigit()
else 0
    )

    # Database
    db_type: str = field(default_factory=lambda: os.getenv("DB_TYPE", "sqlite"))
    db_path: str = field( # Change only 'stromeside'
        default_factory=lambda: os.getenv("DB_PATH", "data/stormside.db")
    )
    postgres_dsn: str = field(
        default_factory=lambda: (
            "postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}".format(
                user=os.getenv("POSTGRES_USER", "bot_user"),
                password=os.getenv("POSTGRES_PASSWORD", ""),
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=os.getenv("POSTGRES_PORT", "5432"),
                db=os.getenv("POSTGRES_DB", "stormside"), # Change only 'stromeside'
            )
        )
    )

    # Proxy (for local testing if Telegram is blocked)
    proxy_url: Optional[str] = field(
        default_factory=lambda: os.getenv("PROXY_URL")
    )

    # RCON
    rcon_host: str = field(default_factory=lambda: os.getenv("RCON_HOST", "127.0.0.1"))
    rcon_port: int = field(
        default_factory=lambda: int(os.getenv("RCON_PORT", "25575"))
    )
    rcon_password: str = field(
        default_factory=lambda: os.getenv("RCON_PASSWORD", "")
    )

    # Payment
    click_qr_path: str = field(
        default_factory=lambda: os.getenv("CLICK_QR_PATH", "assets/click_qr.png")
    )
    payme_qr_path: str = field(
        default_factory=lambda: os.getenv("PAYME_QR_PATH", "assets/payme_qr.png")
    )
    click_card: str = field(
        default_factory=lambda: os.getenv("CLICK_CARD", "0000 0000 0000 0000")
    )
    payme_card: str = field(
        default_factory=lambda: os.getenv("PAYME_CARD", "0000 0000 0000 0000")
    )
    card_holder: str = field( # Change only 'stromeside'
        default_factory=lambda: os.getenv("CARD_HOLDER", "Stormside")
    )
    support_handle: str = field(
        default_factory=lambda: os.getenv("SUPPORT_HANDLE", "@shtursunov7")
    )

    # Logging
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_file: str = field(
        default_factory=lambda: os.getenv("LOG_FILE", "logs/bot.log")
    )

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_ids

    def add_admin(self, user_id: int) -> bool:
        """Yangi admin ID sini xotiraga va .env fayliga saqlaydi."""
        if user_id in self.admin_ids:
            return False
            
        self.admin_ids.append(user_id)
        env_path = BASE_DIR / ".env"
        
        if env_path.exists():
            lines = env_path.read_text().splitlines()
            new_ids_str = ",".join(map(str, self.admin_ids))
            found = False
            
            for i, line in enumerate(lines):
                if line.startswith("ADMIN_IDS="):
                    lines[i] = f"ADMIN_IDS={new_ids_str}"
                    found = True
                    break
            
            if not found:
                lines.append(f"ADMIN_IDS={new_ids_str}")
                
            env_path.write_text("\n".join(lines) + "\n")
        return True


# Singleton
config = Config()
