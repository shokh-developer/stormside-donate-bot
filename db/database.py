"""
db/database.py – SQLite (aiosqlite) database with all table definitions.
Optional PostgreSQL via asyncpg is stubbed and noted where relevant.
"""
from __future__ import annotations

import logging
from pathlib import Path

import aiosqlite

from config import config

logger = logging.getLogger(__name__)

_DB_PATH = Path(config.db_path)


def get_db() -> aiosqlite.Connection:
    """Return a database connection object with row_factory set."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return aiosqlite.connect(_DB_PATH)


# ─── Schema ──────────────────────────────────────────────────────────────────

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id     INTEGER UNIQUE NOT NULL,
    username        TEXT,
    full_name       TEXT,
    mc_nickname     TEXT UNIQUE,
    balance         REAL    DEFAULT 0,
    registered_at   TEXT    DEFAULT (datetime('now')),
    last_seen       TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS products (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    category        TEXT    NOT NULL,   -- 'rank' | 'coins'
    description     TEXT,
    price           REAL    NOT NULL,
    lp_group        TEXT,               -- LuckPerms group name (ranks only)
    coins_amount    INTEGER,            -- for coin packages
    duration_days   INTEGER DEFAULT 0,  -- 0 = permanent
    emoji           TEXT    DEFAULT '🎮',
    is_active       INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS orders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    product_id      INTEGER NOT NULL REFERENCES products(id),
    mc_nickname     TEXT    NOT NULL,
    amount          REAL    NOT NULL,
    payment_method  TEXT    NOT NULL,   -- 'click' | 'payme'
    status          TEXT    DEFAULT 'pending',  -- pending | approved | rejected | delivered
    screenshot_file_id TEXT,
    admin_id        INTEGER,
    admin_note      TEXT,
    rcon_command    TEXT,
    rcon_result     TEXT,
    created_at      TEXT    DEFAULT (datetime('now')),
    updated_at      TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS payments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        INTEGER NOT NULL REFERENCES orders(id),
    user_id         INTEGER NOT NULL REFERENCES users(id),
    amount          REAL    NOT NULL,
    method          TEXT    NOT NULL,
    screenshot_file_id TEXT,
    status          TEXT    DEFAULT 'pending',
    created_at      TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS admin_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id        INTEGER NOT NULL,
    action          TEXT    NOT NULL,
    target_order_id INTEGER,
    note            TEXT,
    created_at      TEXT    DEFAULT (datetime('now'))
);
"""


def _rank_perks(*lines: str) -> str:
    return "✅ Imkoniyatlar:\n\n" + "\n".join(f"• {line}" for line in lines)


# (id, name, category, description, price, lp_group, coins_amount, duration_days, emoji)
SEED_PRODUCTS = [
    # Mist
    (1,  "Mist (1 Oy)",      "rank", _rank_perks(
        "/craft — Shaxsiy verstak", "/salary — Kunlik maosh", "/kits — Shaxsiy kit",
        "2 ta home", "Auksionda 4 ta slot", "Maksimum 3 ta region",
    ), 5000,   "mist",      None, 30, "🌫️"),
    (2,  "Mist (Butunlay)",  "rank", _rank_perks(
        "/craft — Shaxsiy verstak", "/salary — Kunlik maosh", "/kits — Shaxsiy kit",
        "2 ta home", "Auksionda 4 ta slot", "Maksimum 3 ta region",
    ), 20000,  "mist",      None, 0,  "🌫️"),
    # Cloud
    (3,  "Cloud (1 Oy)",     "rank", _rank_perks(
        "Mist rankidagi barcha imkoniyatlar", "/anvil — Shaxsiy anvil",
        "3 ta home", "Auksionda 5 ta slot", "Maksimum 3 ta region",
    ), 8000,   "cloud",     None, 30, "☁️"),
    (4,  "Cloud (Butunlay)", "rank", _rank_perks(
        "Mist rankidagi barcha imkoniyatlar", "/anvil — Shaxsiy anvil",
        "3 ta home", "Auksionda 5 ta slot", "Maksimum 3 ta region",
    ), 30000,  "cloud",     None, 0,  "☁️"),
    # Wind
    (5,  "Wind (1 Oy)",      "rank", _rank_perks(
        "Cloud rankidagi barcha imkoniyatlar", "/ptime — Shaxsiy vaqt", "/pweather — Shaxsiy ob-havo",
        "3 ta home", "Auksionda 5 ta slot", "Maksimum 3 ta region",
    ), 12000,  "wind",      None, 30, "🌬️"),
    (6,  "Wind (Butunlay)",  "rank", _rank_perks(
        "Cloud rankidagi barcha imkoniyatlar", "/ptime — Shaxsiy vaqt", "/pweather — Shaxsiy ob-havo",
        "3 ta home", "Auksionda 5 ta slot", "Maksimum 3 ta region",
    ), 45000,  "wind",      None, 0,  "🌬️"),
    # Breeze
    (7,  "Breeze (1 Oy)",      "rank", _rank_perks(
        "Wind rankidagi barcha imkoniyatlar", "/time — O'yin vaqti", "/weather — O'yin ob-havosi",
        "4 ta home", "Auksionda 5 ta slot", "Maksimum 3 ta region",
    ), 18000,  "breeze",    None, 30, "🍃"),
    (8,  "Breeze (Butunlay)",  "rank", _rank_perks(
        "Wind rankidagi barcha imkoniyatlar", "/time — O'yin vaqti", "/weather — O'yin ob-havosi",
        "4 ta home", "Auksionda 5 ta slot", "Maksimum 3 ta region",
    ), 60000,  "breeze",    None, 0,  "🍃"),
    # Thunder
    (9,  "Thunder (1 Oy)",     "rank", _rank_perks(
        "Breeze rankidagi barcha imkoniyatlar", "/eat — Ochlikni to'ldirish", "/head — O'yinchi boshini olish",
        "5 ta home", "Auksionda 5 ta slot", "Maksimum 4 ta region",
    ), 25000,  "thunder",   None, 30, "🌩️"),
    (10, "Thunder (Butunlay)", "rank", _rank_perks(
        "Breeze rankidagi barcha imkoniyatlar", "/eat — Ochlikni to'ldirish", "/head — O'yinchi boshini olish",
        "5 ta home", "Auksionda 5 ta slot", "Maksimum 4 ta region",
    ), 80000,  "thunder",   None, 0,  "🌩️"),
    # Hurricane
    (11, "Hurricane (1 Oy)",     "rank", _rank_perks(
        "Thunder rankidagi barcha imkoniyatlar", "/heal — Jon va ochlikni to'ldirish", "/rtpdal — O'yinchilardan uzoq RTP",
        "5 ta home", "Auksionda 6 ta slot", "Maksimum 4 ta region",
    ), 35000,  "hurricane", None, 30, "🌀"),
    (12, "Hurricane (Butunlay)", "rank", _rank_perks(
        "Thunder rankidagi barcha imkoniyatlar", "/heal — Jon va ochlikni to'ldirish", "/rtpdal — O'yinchilardan uzoq RTP",
        "5 ta home", "Auksionda 6 ta slot", "Maksimum 4 ta region",
    ), 110000, "hurricane", None, 0,  "🌀"),
    # Tornado
    (13, "Tornado (1 Oy)",     "rank", _rank_perks(
        "Hurricane rankidagi barcha imkoniyatlar", "/inv — Inventarni ko'rish", "/stack — Narsalarni stack qilish",
        "6 ta home", "Auksionda 6 ta slot", "Maksimum 4 ta region",
    ), 45000,  "tornado",   None, 30, "🌪️"),
    (14, "Tornado (Butunlay)", "rank", _rank_perks(
        "Hurricane rankidagi barcha imkoniyatlar", "/inv — Inventarni ko'rish", "/stack — Narsalarni stack qilish",
        "6 ta home", "Auksionda 6 ta slot", "Maksimum 4 ta region",
    ), 145000, "tornado",   None, 0,  "🌪️"),
    # Tempest
    (15, "Tempest (1 Oy)",     "rank", _rank_perks(
        "Tornado rankidagi barcha imkoniyatlar",
        "6 ta home", "Auksionda 6 ta slot", "Maksimum 5 ta region",
    ), 55000,  "tempest",   None, 30, "🌊"),
    (16, "Tempest (Butunlay)", "rank", _rank_perks(
        "Tornado rankidagi barcha imkoniyatlar",
        "6 ta home", "Auksionda 6 ta slot", "Maksimum 5 ta region",
    ), 190000, "tempest",   None, 0,  "🌊"),
    # Night
    (17, "Night (1 Oy)",     "rank", _rank_perks(
        "Tempest rankidagi barcha imkoniyatlar", "/salary+ — Sapphire valyutasida maxsus maosh",
        "6 ta home", "Auksionda 6 ta slot", "Maksimum 6 ta region",
    ), 170000, "night",     None, 30, "🌙"),
    (18, "Night (Butunlay)", "rank", _rank_perks(
        "Tempest rankidagi barcha imkoniyatlar", "/salary+ — Sapphire valyutasida maxsus maosh",
        "6 ta home", "Auksionda 6 ta slot", "Maksimum 6 ta region",
    ), 250000, "night",     None, 0,  "🌙"),
    # Sun
    (19, "Sun (1 Oy)",     "rank", _rank_perks(
        "Night rankidagi barcha imkoniyatlar", "/kick — O'yinchini chiqarish (qoidalarga asosan)", "/repair all — Barcha narsalarni tuzatish",
        "9 ta home", "Auksionda 9 ta slot", "Maksimum 9 ta region",
    ), 90000,  "sun",       None, 30, "☀️"),
    (20, "Sun (Butunlay)", "rank", _rank_perks(
        "Night rankidagi barcha imkoniyatlar", "/kick — O'yinchini chiqarish (qoidalarga asosan)", "/repair all — Barcha narsalarni tuzatish",
        "9 ta home", "Auksionda 9 ta slot", "Maksimum 9 ta region",
    ), 320000, "sun",       None, 0,  "☀️"),
    # Storm
    (21, "Storm (1 Oy)",     "rank", "👑 Eng yuqori rank\n\n" + _rank_perks(
        "Sun rankidagi barcha imkoniyatlar", "/ban — O'yinchilarga ban berish (qoidalarga asosan)",
        "/elytrafly — Elytra bilan uchish", "Kuchli maxsus kit", "Maxsus rangli prefix",
        "/salary+ — Sapphire valyutasida maxsus maosh", "15 ta home", "Auksionda 15 ta slot", "Maksimum 15 ta region",
    ), 145000, "storm",     None, 30, "⚡"),
    (22, "Storm (Butunlay)", "rank", "👑 Eng yuqori rank\n\n" + _rank_perks(
        "Sun rankidagi barcha imkoniyatlar", "/ban — O'yinchilarga ban berish (qoidalarga asosan)",
        "/elytrafly — Elytra bilan uchish", "Kuchli maxsus kit", "Maxsus rangli prefix",
        "/salary+ — Sapphire valyutasida maxsus maosh", "15 ta home", "Auksionda 15 ta slot", "Maksimum 15 ta region",
    ), 400000, "storm",     None, 0,  "⚡"),
    # SIDE (Vales)
    (23, "100 Vales",  "coins", "🤑 100 Vales — o'yin ichidagi valyuta",  10000,  None, 100,  0, "🤑"),
    (24, "500 Vales",  "coins", "🤑 500 Vales — o'yin ichidagi valyuta",  45000,  None, 500,  0, "🤑"),
    (25, "1000 Vales", "coins", "🤑 1000 Vales — o'yin ichidagi valyuta", 85000,  None, 1000, 0, "🤑"),
    (26, "2500 Vales", "coins", "🤑 2500 Vales — o'yin ichidagi valyuta", 200000, None, 2500, 0, "🤑"),
    # Cases
    (27, "Donate Case", "case", "🎁 Donate Case — maxsus mukofotlar",      25000, None, None, 0, "🎁"),
    (28, "Token Case",  "case", "🎁 Token Case — token sovrinlar",         20000, None, None, 0, "🎁"),
    (29, "Kit Case",    "case", "🎁 Kit Case — asbob-uskunalar to'plami",  10000, None, None, 0, "🎁"),
    # Unban
    (30, "UNBAN", "unban", "✔️ Hisobingizni razblokirovka qiling", 30000, None, None, 0, "✔️"),
]

_UPSERT_PRODUCT_SQL = """
INSERT INTO products (id, name, category, description, price, lp_group, coins_amount, duration_days, emoji)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
    name=excluded.name,
    category=excluded.category,
    description=excluded.description,
    price=excluded.price,
    lp_group=excluded.lp_group,
    coins_amount=excluded.coins_amount,
    duration_days=excluded.duration_days,
    emoji=excluded.emoji
"""


async def init_db() -> None:
    logger.info("Initialising database at %s", _DB_PATH)
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        await db.executescript(SCHEMA)
        await db.executemany(_UPSERT_PRODUCT_SQL, SEED_PRODUCTS)
        await db.commit()
    logger.info("Database ready.")
