"""
handlers/start.py – /start command and profile management.
"""
from __future__ import annotations

import logging
import re

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ContentType

from config import config
from db import repository as repo
from keyboards import keyboards as kb
from services.rcon_service import rcon
from utils.helpers import profile_text, validate_mc_nickname, welcome_text

logger = logging.getLogger(__name__)
router = Router(name="start")

class NicknameForm(StatesGroup):
    waiting_for_nickname = State()

async def get_server_stats() -> str:
    """Fetch player count from Minecraft server via RCON."""
    try:
        # Minecraft 'list' command usually returns: 
        # "There are 2 of a max 20 players online: player1, player2"
        success, response = await rcon.send_command("list")
        if not success:
            return "Offline"
            
        # Ko'proq formatlarni qo'llab-quvvatlash uchun (masalan: 1/20 yoki 1 of a max of 20)
        # re.search(r"(\d+)\D+(\d+)", response) birinchi kelgan ikkita sonni oladi
        match = re.search(r"(\d+)\D+(\d+)", response)
        if match:
            return f"{match.group(1)} / {match.group(2)}"
        return "Online"
    except Exception as e:
        logger.warning(f"Failed to fetch RCON stats: {e}")
        return "Noma'lum"


# ──────────────────────────────────────────────────────────────────────────────
# /start
# ──────────────────────────────────────────────────────────────────────────────

@router.message(Command("start"))
async def cmd_start(message: Message, db_user: dict) -> None:
    stats = await get_server_stats()
    nick = db_user.get('mc_nickname') or "Bog'lanmagan"
    
    clan = "None"
    rank = "Default"
    if db_user.get('mc_nickname'):
        clan = await rcon.get_player_clan(db_user['mc_nickname'])
        rank = await rcon.get_player_rank(db_user['mc_nickname'])

    text = welcome_text(
        message.from_user.full_name, 
        stats, 
        nick, 
        clan, 
        rank
    )
    await message.answer(
        text,
        reply_markup=kb.main_menu(),
    )


@router.callback_query(F.data == "home")
async def cb_home(call: CallbackQuery, db_user: dict) -> None:
    stats = await get_server_stats()
    nick = db_user.get('mc_nickname') or "Bog'lanmagan"
    
    clan = "None"
    rank = "Default"
    if db_user.get('mc_nickname'):
        clan = await rcon.get_player_clan(db_user['mc_nickname'])
        rank = await rcon.get_player_rank(db_user['mc_nickname'])

    text = welcome_text(
        call.from_user.full_name, 
        stats, 
        nick, 
        clan, 
        rank
    )
    
    # Foto xabarlarda edit_text ishlamasligini oldini olish
    if call.message.photo:
        await call.message.delete()
        await call.message.answer(text, reply_markup=kb.main_menu())
    else:
        try:
            await call.message.edit_text(
                text,
                reply_markup=kb.main_menu(),
            )
        except Exception:
            await call.message.answer(text, reply_markup=kb.main_menu())
            await call.message.delete()
            
    await call.answer()


# ──────────────────────────────────────────────────────────────────────────────
# Profile
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
# Order History
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
        from utils.helpers import order_summary, STATUS_EMOJI
        lines = [f"📋 <b>Oxirgi {len(orders)} ta buyurtmalaringiz</b>\n"]
        for o in orders:
            emoji = STATUS_EMOJI.get(o["status"], "❓")
            lines.append(
                f"{emoji} <b>#{o['id']}</b>  {o.get('emoji','🎮')} {o['product_name']}  "
                f"— {o['created_at'][:10]}"
            )
        text = "\n".join(lines)

    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.back_home(),
    )
    await call.answer()


# ──────────────────────────────────────────────────────────────────────────────
# Help
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
