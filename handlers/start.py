"""
handlers/start.py – /start command, profile management, and main-menu text handlers.
"""
from __future__ import annotations

import logging
import re

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from config import config
from db import repository as repo
from keyboards import keyboards as kb
from services.rcon_service import rcon
from utils.helpers import (
    STATUS_EMOJI, order_summary, profile_text, validate_mc_nickname, welcome_text
)

logger = logging.getLogger(__name__)
router = Router(name="start")


class NicknameForm(StatesGroup):
    waiting_for_nickname = State()


async def get_server_stats() -> str:
    try:
        success, response = await rcon.send_command("list")
        if not success:
            return "Offline"
        match = re.search(r"(\d+)\D+(\d+)", response)
        if match:
            return f"{match.group(1)} / {match.group(2)}"
        return "Online"
    except Exception as exc:
        logger.warning("Failed to fetch RCON stats: %s", exc)
        return "Noma'lum"


async def _build_welcome(user_id: int, full_name: str, mc_nickname: str | None) -> str:
    stats = await get_server_stats()
    nick = mc_nickname or "Bog'lanmagan"
    rank = "Default"
    if mc_nickname:
        rank = await rcon.get_player_rank(mc_nickname)
    return welcome_text(full_name, stats, nick, rank)


# ──────────────────────────────────────────────────────────────────────────────
# /start
# ──────────────────────────────────────────────────────────────────────────────

@router.message(Command("start"))
async def cmd_start(message: Message, db_user: dict) -> None:
    text = await _build_welcome(
        message.from_user.id,
        message.from_user.full_name,
        db_user.get("mc_nickname"),
    )
    await message.answer(text, reply_markup=kb.main_menu())


@router.callback_query(F.data == "home")
async def cb_home(call: CallbackQuery, db_user: dict) -> None:
    text = await _build_welcome(
        call.from_user.id,
        call.from_user.full_name,
        db_user.get("mc_nickname"),
    )
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.message.answer(text, reply_markup=kb.main_menu())
    await call.answer()


# ──────────────────────────────────────────────────────────────────────────────
# Main-menu reply-keyboard handlers
# ──────────────────────────────────────────────────────────────────────────────

@router.message(F.text == "👤 Profil")
async def msg_profile(message: Message, db_user: dict) -> None:
    orders = await repo.get_user_orders(message.from_user.id, limit=100)
    await message.answer(
        profile_text(db_user, len(orders)),
        parse_mode="HTML",
        reply_markup=kb.profile_menu(has_nickname=bool(db_user.get("mc_nickname"))),
    )


@router.message(F.text == "📋 Buyurtmalar")
async def msg_orders(message: Message) -> None:
    orders = await repo.get_user_orders(message.from_user.id, limit=10)
    if not orders:
        text = (
            "📋 <b>Buyurtmalar tarixi</b>\n\n"
            "Sizda hali hech qanday buyurtma yo'q.\n"
            "Do'kon bo'limiga o'ting!"
        )
    else:
        lines = [f"📋 <b>Oxirgi {len(orders)} ta buyurtmalaringiz</b>\n"]
        for o in orders:
            emoji = STATUS_EMOJI.get(o["status"], "❓")
            lines.append(
                f"{emoji} <b>#{o['id']}</b>  {o.get('emoji', '🎮')} {o['product_name']}"
                f"  — {o['created_at'][:10]}"
            )
        text = "\n".join(lines)
    await message.answer(text, parse_mode="HTML", reply_markup=kb.back_home())


@router.message(F.text == "ℹ️ Ma'lumotlar")
async def msg_help(message: Message) -> None:
    await message.answer(
        "ℹ️ <b>Yordam va ko'p beriladigan savollar</b>\n\n"
        "1️⃣ Profil bo'limida Minecraft Nicknameingizni bog'lang\n"
        "2️⃣ Do'kondan Rank yoki tanga paketini tanlang\n"
        "3️⃣ Click yoki Payme orqali to'lov qiling\n"
        "4️⃣ To'lov chekini (screenshot) yuboring\n"
        "5️⃣ Admin tekshiradi va buyurtmani tasdiqlaydi\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🌐 Server IP: <code>stormside.uz</code>\n"
        "📞 Support: @shtursunov7\n"
        "⏱ Rankni berish vaqti: odatda 1 soat ichida\n",
        parse_mode="HTML",
        reply_markup=kb.back_home(),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Profile (callback – from inline menus)
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "profile")
async def cb_profile(call: CallbackQuery, db_user: dict) -> None:
    orders = await repo.get_user_orders(call.from_user.id, limit=100)
    await call.message.edit_text(
        profile_text(db_user, len(orders)),
        parse_mode="HTML",
        reply_markup=kb.profile_menu(has_nickname=bool(db_user.get("mc_nickname"))),
    )
    await call.answer()


# ──────────────────────────────────────────────────────────────────────────────
# Nickname binding
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "set_nickname")
async def cb_set_nickname(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(NicknameForm.waiting_for_nickname)
    await call.message.edit_text(
        "🎮 <b>Minecraft Nicknameingizni bog'lang</b>\n\n"
        "Iltimos, o'yin ichidagi <b>aniq</b> nomingizni yozing.\n\n"
        "Qoidalar: 3-16 ta belgi, faqat harf, raqam va pastki chiziq.\n\n"
        "<i>Misol: </i> <code>CoolPlayer_99</code>",
        parse_mode="HTML",
        reply_markup=kb.back_home(),
    )
    await call.answer()


@router.message(NicknameForm.waiting_for_nickname)
async def receive_nickname(message: Message, state: FSMContext) -> None:
    nick = message.text.strip() if message.text else ""

    if not validate_mc_nickname(nick):
        await message.answer(
            "❌ <b>Noto'g'ri Nickname!</b>\n\n"
            "3–16 ta belgi bo'lishi kerak: faqat harf, raqam va pastki chiziq.\n"
            "Qaytadan urunib ko'ring:",
            parse_mode="HTML",
            reply_markup=kb.back_home(),
        )
        return

    await repo.set_mc_nickname(message.from_user.id, nick)
    await state.clear()
    await message.answer(
        f"✅ <b>Nickname bog'landi!</b>\n\n"
        f"🎮 Sizning Minecraft ismingiz: <b>{nick}</b>\n\n"
        f"Endi bemalol Rank va tangalar sotib olishingiz mumkin!",
        parse_mode="HTML",
        reply_markup=kb.main_menu(),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Order History (callback – from inline menus)
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "my_orders")
async def cb_my_orders(call: CallbackQuery) -> None:
    orders = await repo.get_user_orders(call.from_user.id, limit=10)

    if not orders:
        text = (
            "📋 <b>Buyurtmalar tarixi</b>\n\n"
            "Sizda hali hech qanday buyurtma yo'q.\n"
            "Do'kon bo'limiga o'ting!"
        )
    else:
        lines = [f"📋 <b>Oxirgi {len(orders)} ta buyurtmalaringiz</b>\n"]
        for o in orders:
            emoji = STATUS_EMOJI.get(o["status"], "❓")
            lines.append(
                f"{emoji} <b>#{o['id']}</b>  {o.get('emoji', '🎮')} {o['product_name']}"
                f"  — {o['created_at'][:10]}"
            )
        text = "\n".join(lines)

    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb.back_home())
    await call.answer()


# ──────────────────────────────────────────────────────────────────────────────
# Help (callback – from inline menus)
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "help")
async def cb_help(call: CallbackQuery) -> None:
    await call.message.edit_text(
        "ℹ️ <b>Yordam va ko'p beriladigan savollar</b>\n\n"
        "1️⃣ Profil bo'limida Minecraft Nicknameingizni bog'lang\n"
        "2️⃣ Do'kondan Rank yoki tanga paketini tanlang\n"
        "3️⃣ Click yoki Payme orqali to'lov qiling\n"
        "4️⃣ To'lov chekini (screenshot) yuboring\n"
        "5️⃣ Admin tekshiradi va buyurtmani tasdiqlaydi\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🌐 Server IP: <code>stormside.uz</code>\n"
        "📞 Support: @shtursunov7\n"
        "⏱ Rankni berish vaqti: odatda 1 soat ichida\n",
        parse_mode="HTML",
        reply_markup=kb.back_home(),
    )
    await call.answer()
