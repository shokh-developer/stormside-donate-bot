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

-- Seed default products if none exist
INSERT OR IGNORE INTO products (id, name, category, description, price, lp_group, coins_amount, duration_days, emoji)
VALUES
  -- ECLIPSE
  (1,  'ECLIPSE (1 Oy)',      'rank', '🌑 1 oylik ECLIPSE ranki',          7000,   'eclipse',  NULL, 30, '🌑'),
  (2,  'ECLIPSE (Butunlay)',  'rank', '🌑 Doimiy ECLIPSE ranki',           20000,  'eclipse',  NULL, 0,  '🌑'),
  -- PHOENIX
  (3,  'PHOENIX (1 Oy)',      'rank', '🛡 1 oylik PHOENIX ranki',          12000,  'phoenix',  NULL, 30, '🛡'),
  (4,  'PHOENIX (Butunlay)',  'rank', '🛡 Doimiy PHOENIX ranki',           30000,  'phoenix',  NULL, 0,  '🛡'),
  -- ORACLE
  (5,  'ORACLE (1 Oy)',       'rank', '🪙 1 oylik ORACLE ranki',           18000,  'oracle',   NULL, 30, '🪙'),
  (6,  'ORACLE (Butunlay)',   'rank', '🪙 Doimiy ORACLE ranki',            45000,  'oracle',   NULL, 0,  '🪙'),
  -- VOYAGER
  (7,  'VOYAGER (1 Oy)',      'rank', '⚒️ 1 oylik VOYAGER ranki',         25000,  'voyager',  NULL, 30, '⚒️'),
  (8,  'VOYAGER (Butunlay)',  'rank', '⚒️ Doimiy VOYAGER ranki',          60000,  'voyager',  NULL, 0,  '⚒️'),
  -- CATALYST
  (9,  'CATALYST (1 Oy)',     'rank', '🔪 1 oylik CATALYST ranki',         35000,  'catalyst', NULL, 30, '🔪'),
  (10, 'CATALYST (Butunlay)', 'rank', '🔪 Doimiy CATALYST ranki',          80000,  'catalyst', NULL, 0,  '🔪'),
  -- CELESTIAL
  (11, 'CELESTIAL (1 Oy)',    'rank', '💎 1 oylik CELESTIAL ranki',        50000,  'celestial',NULL, 30, '💎'),
  (12, 'CELESTIAL (Butunlay)','rank', '💎 Doimiy CELESTIAL ranki',         110000, 'celestial',NULL, 0,  '💎'),
  -- AURORA
  (13, 'AURORA (1 Oy)',       'rank', '⚡️ 1 oylik AURORA ranki',           65000,  'aurora',   NULL, 30, '⚡️'),
  (14, 'AURORA (Butunlay)',   'rank', '⚡️ Doimiy AURORA ranki',            145000, 'aurora',   NULL, 0,  '⚡️'),
  -- IMMORTAL
  (15, 'IMMORTAL (1 Oy)',     'rank', '⚡️ 1 oylik IMMORTAL ranki',         80000,  'immortal', NULL, 30, '⚡️'),
  (16, 'IMMORTAL (Butunlay)', 'rank', '⚡️ Doimiy IMMORTAL ranki',          190000, 'immortal', NULL, 0,  '⚡️'),
  -- APEX
  (17, 'APEX (1 Oy)',         'rank', '🌟 1 oylik APEX ranki',             100000, 'apex',     NULL, 30, '🌟'),
  (18, 'APEX (Butunlay)',     'rank', '🌟 Doimiy APEX ranki',              250000, 'apex',     NULL, 0,  '🌟'),
  -- LUMINARY
  (19, 'LUMINARY (1 Oy)',     'rank', '🤩 1 oylik LUMINARY ranki',         125000, 'luminary', NULL, 30, '🤩'),
  (20, 'LUMINARY (Butunlay)', 'rank', '🤩 Doimiy LUMINARY ranki',          320000, 'luminary', NULL, 0,  '🤩'),
  -- GREAT
  (21, 'GREAT (1 Oy)',        'rank', '👑 1 oylik GREAT ranki',            150000, 'great',    NULL, 30, '👑'),
  (22, 'GREAT (Butunlay)',    'rank', '👑 Doimiy GREAT ranki',             400000, 'great',    NULL, 0,  '👑'),
  -- SIDE (Vales)
  (23, '100 Vales',           'coins', '🤑 100 Vales — o''yin ichidagi valyuta',   10000,  NULL, 100,  0, '🤑'),
  (24, '500 Vales',           'coins', '🤑 500 Vales — o''yin ichidagi valyuta',   45000,  NULL, 500,  0, '🤑'),
  (25, '1000 Vales',          'coins', '🤑 1000 Vales — o''yin ichidagi valyuta',  85000,  NULL, 1000, 0, '🤑'),
  (26, '2500 Vales',          'coins', '🤑 2500 Vales — o''yin ichidagi valyuta',  200000, NULL, 2500, 0, '🤑'),
  -- Cases
  (27, 'Donate Case',         'case',  '🎁 Donate Case — maxsus mukofotlar',       25000,  NULL, NULL, 0, '🎁'),
  (28, 'Token Case',          'case',  '🎁 Token Case — token sovrinlar',          20000,  NULL, NULL, 0, '🎁'),
  (29, 'Kit Case',            'case',  '🎁 Kit Case — asbob-uskunalar to''plami',  10000,  NULL, NULL, 0, '🎁'),
  -- Unban
  (30, 'UNBAN',               'unban', '✔️ Hisobingizni razblokirovka qiling',     30000,  NULL, NULL, 0, '✔️');
"""


async def init_db() -> None:
    logger.info("Initialising database at %s", _DB_PATH)
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        await db.executescript(SCHEMA)
        await db.commit()
    logger.info("Database ready.")
