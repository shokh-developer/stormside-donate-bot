"""
utils/helpers.py – formatting, validation, and text utilities.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, Optional


# ──────────────────────────────────────────────────────────────────────────────
# Minecraft nickname validation
# ──────────────────────────────────────────────────────────────────────────────

MC_NICK_RE = re.compile(r"^[a-zA-Z0-9_]{3,16}$")


def validate_mc_nickname(nick: str) -> bool:
    """Validate Minecraft nickname (3-16 chars, alphanumeric + underscore)."""
    return bool(MC_NICK_RE.match(nick))


# ──────────────────────────────────────────────────────────────────────────────
# Price formatting
# ──────────────────────────────────────────────────────────────────────────────

def fmt_price(amount: float) -> str:
    return f"{int(amount):,} UZS".replace(",", " ")


# ──────────────────────────────────────────────────────────────────────────────
# Order status display
# ──────────────────────────────────────────────────────────────────────────────

STATUS_EMOJI = {
    "pending":   "⏳",
    "approved":  "✅",
    "delivered": "🎉",
    "rejected":  "❌",
}

STATUS_TEXT = {
    "pending":   "Pending Review",
    "approved":  "Approved",
    "delivered": "Delivered ✓",
    "rejected":  "Rejected",
}


def status_badge(status: str) -> str:
    return f"{STATUS_EMOJI.get(status, '❓')} {STATUS_TEXT.get(status, status.title())}"


# ──────────────────────────────────────────────────────────────────────────────
# Message templates
# ──────────────────────────────────────────────────────────────────────────────

def welcome_text(full_name: str, stats: str, nickname: str, clan: str = "None", rank: str = "Default") -> str:
    status = "🟢 Online" if stats != "Offline" else "🔴 Offline"
    players = stats if stats != "Offline" else "0"
    
    return (
        f"⚡️ <b>STROMESIDE</b>\n\n"
        f"👋 Salom, <b>{full_name}</b>\n\n"
        f"📌 <b>SERVER STATISTIKASI:</b>\n"
        f"├ 🖥 IP: <code>mc.stremeside.uz</code>\n"
        f"├ 📊 Holat: {status}\n"
        f"└ 👥 Oʻyinchilar: <b>{players}</b>\n\n"
        f"👤 <b>PROFILINGIZ:</b>\n"
        f"├ 🎮 Nik: <code>{nickname}</code>\n"
        f"├ 🛡 Klan: <b>{clan}</b>\n"
        f"└ 🎖 Rank: <b>{rank}</b>\n\n"
        f"Botdan foydalanish uchun quyidagi menyuni tanlang 👇"
    )

def profile_text(user: Dict[str, Any], orders_count: int) -> str:
    nick = user.get("mc_nickname") or "❌ Not linked"
    username = f"@{user['username']}" if user.get("username") else "—"
    registered = user.get("registered_at", "")[:10]
    return (
        f"👤 <b>Your Profile</b>\n\n"
        f"🪪 Name:         <b>{user['full_name']}</b>\n"
        f"📱 Telegram:     {username}\n"
        f"🎮 MC Nickname:  <b>{nick}</b>\n"
        f"📦 Total Orders: <b>{orders_count}</b>\n"
        f"📅 Member Since: <b>{registered}</b>\n"
    )


def product_card(p: Dict[str, Any]) -> str:
    duration = "Permanent" if not p.get("duration_days") else f"{p['duration_days']} days"
    extras = ""
    if p["category"] == "rank":
        extras = f"🏅 Type:       <b>Rank ({duration})</b>\n"
    elif p["category"] == "coins":
        extras = f"🪙 Coins:      <b>{p.get('coins_amount', 0):,}</b>\n"

    return (
        f"{p['emoji']} <b>{p['name']}</b>\n\n"
        f"{p.get('description', '')}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{extras}"
        f"💵 Price:      <b>{fmt_price(p['price'])}</b>\n"
    )


def order_summary(order: Dict[str, Any]) -> str:
    return (
        f"📦 <b>Order #{order['id']}</b>\n\n"
        f"{order.get('emoji', '🎮')} Product:  <b>{order['product_name']}</b>\n"
        f"🎮 Nickname: <b>{order['mc_nickname']}</b>\n"
        f"💵 Amount:   <b>{fmt_price(order['amount'])}</b>\n"
        f"💳 Method:   {order['payment_method'].upper()}\n"
        f"📊 Status:   {status_badge(order['status'])}\n"
        f"🕐 Date:     {order.get('created_at', '')[:16]}\n"
    )


def admin_order_text(order: Dict[str, Any]) -> str:
    user_info = (
        f"@{order['user_username']}" if order.get("user_username")
        else order.get("user_full_name", "Unknown")
    )
    return (
        f"🔔 <b>New Order #{order['id']}</b>\n\n"
        f"👤 User:     {user_info} (<code>{order['telegram_id']}</code>)\n"
        f"🎮 Nickname: <b>{order['mc_nickname']}</b>\n"
        f"{order.get('emoji','🎮')} Product:  <b>{order['product_name']}</b>\n"
        f"💵 Amount:   <b>{fmt_price(order['amount'])}</b>\n"
        f"💳 Method:   {order['payment_method'].upper()}\n"
        f"🕐 Time:     {order.get('created_at', '')[:16]}\n"
    )


def qr_instructions(
    method: str,
    amount: float,
    card: str,
    holder: str,
    order_id: int,
) -> str:
    method_name = "Click" if method == "click" else "Payme"
    return (
        f"💳 <b>Pay via {method_name}</b>\n\n"
        f"📋 Order:   <b>#{order_id}</b>\n"
        f"💵 Amount:  <b>{fmt_price(amount)}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏦 Card Number:\n"
        f"<code>{card}</code>\n"
        f"👤 Card Holder: <b>{holder}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📸 After payment, press the button below\n"
        f"and <b>send a screenshot</b> of the payment.\n\n"
        f"⚠️ Orders without screenshots cannot be verified!"
    )
