"""
db/repository.py – all database read/write helpers.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import aiosqlite

from db.database import get_db


# ──────────────────────────────────────────────────────────────────────────────
# Users
# ──────────────────────────────────────────────────────────────────────────────

async def upsert_user(
    telegram_id: int,
    username: Optional[str],
    full_name: Optional[str],
) -> Dict[str, Any]:
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            """
            INSERT INTO users (telegram_id, username, full_name)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username  = excluded.username,
                full_name = excluded.full_name,
                last_seen = datetime('now')
            """,
            (telegram_id, username, full_name),
        )
        await db.commit()
        async with db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row)


async def get_user(telegram_id: int) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def get_all_users() -> List[Dict[str, Any]]:
    """Get all registered users for broadcasting news."""
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT telegram_id FROM users") as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def set_mc_nickname(telegram_id: int, nickname: str) -> None:
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "UPDATE users SET mc_nickname = ? WHERE telegram_id = ?",
            (nickname, telegram_id),
        )
        await db.commit()


async def get_user_orders(telegram_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT o.*, p.name as product_name, p.emoji
            FROM orders o
            JOIN users u ON u.id = o.user_id
            JOIN products p ON p.id = o.product_id
            WHERE u.telegram_id = ?
            ORDER BY o.created_at DESC LIMIT ?
            """,
            (telegram_id, limit),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

async def get_top_donators(limit: int = 10) -> List[Dict[str, Any]]:
    """Get users who spent the most on approved orders."""
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT u.full_name, u.mc_nickname, SUM(o.amount) as total_spent
            FROM orders o
            JOIN users u ON u.id = o.user_id
            WHERE o.status IN ('approved', 'delivered')
            GROUP BY u.id
            ORDER BY total_spent DESC LIMIT ?
            """,
            (limit,),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

# ──────────────────────────────────────────────────────────────────────────────
# Products
# ──────────────────────────────────────────────────────────────────────────────

async def get_products(category: Optional[str] = None) -> List[Dict[str, Any]]:
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        if category:
            async with db.execute(
                "SELECT * FROM products WHERE is_active = 1 AND category = ? ORDER BY price",
                (category,),
            ) as cur:
                rows = await cur.fetchall()
        else:
            async with db.execute(
                "SELECT * FROM products WHERE is_active = 1 ORDER BY category, price"
            ) as cur:
                rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def get_all_products() -> List[Dict[str, Any]]:
    """Get all products including inactive ones for admin management."""
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM products ORDER BY category, price"
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def add_product(
    name: str,
    category: str,
    price: float,
    emoji: str,
    lp_group: Optional[str] = None,
    coins_amount: Optional[int] = None,
    duration_days: int = 0,
) -> None:
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO products (name, category, price, emoji, lp_group, coins_amount, duration_days, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (name, category, price, emoji, lp_group, coins_amount, duration_days),
        )
        await db.commit()


async def update_product_price(product_id: int, price: float) -> None:
    async with get_db() as db:
        await db.execute(
            "UPDATE products SET price = ? WHERE id = ?",
            (price, product_id),
        )
        await db.commit()


async def toggle_product_status(product_id: int, is_active: bool) -> None:
    async with get_db() as db:
        await db.execute(
            "UPDATE products SET is_active = ? WHERE id = ?",
            (1 if is_active else 0, product_id),
        )
        await db.commit()


async def get_product(product_id: int) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


# ──────────────────────────────────────────────────────────────────────────────
# Orders
# ──────────────────────────────────────────────────────────────────────────────

async def create_order(
    telegram_id: int,
    product_id: int,
    mc_nickname: str,
    amount: float,
    payment_method: str,
    screenshot_file_id: Optional[str] = None,
) -> int:
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cur:
            row = await cur.fetchone()
        if not row:
            raise ValueError("User not found")
        user_db_id = row["id"]

        async with db.execute(
            """
            INSERT INTO orders
              (user_id, product_id, mc_nickname, amount, payment_method, screenshot_file_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_db_id, product_id, mc_nickname, amount, payment_method, screenshot_file_id),
        ) as cur:
            order_id = cur.lastrowid

        await db.execute(
            """
            INSERT INTO payments (order_id, user_id, amount, method, screenshot_file_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (order_id, user_db_id, amount, payment_method, screenshot_file_id),
        )
        await db.commit()
        return order_id


async def get_order(order_id: int) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT o.*, p.name as product_name, p.emoji, p.lp_group,
                   p.coins_amount, p.category,
                   u.telegram_id, u.mc_nickname as user_mc_nickname,
                   u.full_name as user_full_name, u.username as user_username
            FROM orders o
            JOIN products p ON p.id = o.product_id
            JOIN users u ON u.id = o.user_id
            WHERE o.id = ?
            """,
            (order_id,),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_pending_orders() -> List[Dict[str, Any]]:
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT o.*, p.name as product_name, p.emoji,
                   u.telegram_id, u.full_name as user_full_name,
                   u.username as user_username
            FROM orders o
            JOIN products p ON p.id = o.product_id
            JOIN users u ON u.id = o.user_id
            WHERE o.status = 'pending'
            ORDER BY o.created_at ASC
            """
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def update_order_status(
    order_id: int,
    status: str,
    admin_id: Optional[int] = None,
    admin_note: Optional[str] = None,
    rcon_command: Optional[str] = None,
    rcon_result: Optional[str] = None,
) -> None:
    async with get_db() as db:
        await db.execute(
            """
            UPDATE orders SET
                status       = ?,
                admin_id     = COALESCE(?, admin_id),
                admin_note   = COALESCE(?, admin_note),
                rcon_command = COALESCE(?, rcon_command),
                rcon_result  = COALESCE(?, rcon_result),
                updated_at   = datetime('now')
            WHERE id = ?
            """,
            (status, admin_id, admin_note, rcon_command, rcon_result, order_id),
        )
        await db.execute(
            "UPDATE payments SET status = ? WHERE order_id = ?",
            (status, order_id),
        )
        await db.commit()


async def update_order_screenshot(order_id: int, screenshot_file_id: str) -> None:
    """Save the payment screenshot file ID to an order."""
    async with get_db() as db:
        await db.execute(
            "UPDATE orders SET screenshot_file_id = ?, updated_at = datetime('now') WHERE id = ?",
            (screenshot_file_id, order_id),
        )
        await db.commit()


async def has_pending_order(telegram_id: int, product_id: int) -> bool:
    """Prevent duplicate pending orders for same user+product."""
    async with get_db() as db:
        async with db.execute(
            """
            SELECT 1 FROM orders o
            JOIN users u ON u.id = o.user_id
            WHERE u.telegram_id = ? AND o.product_id = ? AND o.status = 'pending'
            """,
            (telegram_id, product_id),
        ) as cur:
            return bool(await cur.fetchone())


# ──────────────────────────────────────────────────────────────────────────────
# Admin Logs
# ──────────────────────────────────────────────────────────────────────────────

async def log_admin_action(
    admin_id: int,
    action: str,
    target_order_id: Optional[int] = None,
    note: Optional[str] = None,
) -> None:
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO admin_logs (admin_id, action, target_order_id, note)
            VALUES (?, ?, ?, ?)
            """,
            (admin_id, action, target_order_id, note),
        )
        await db.commit()
