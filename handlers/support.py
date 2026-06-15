from __future__ import annotations
import logging
from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import config
from db import repository as repo
from keyboards import keyboards as kb
from utils.helpers import fmt_price

logger = logging.getLogger(__name__)
router = Router(name="support")

class SupportState(StatesGroup):
    waiting_for_ticket = State()
    waiting_for_admin_reply = State()

# ──────────────────────────────────────────────────────────────────────────────
# Top Donators
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "top_donators")
async def cb_top_donators(call: CallbackQuery) -> None:
    tops = await repo.get_top_donators()
    if not tops:
        text = "🏆 <b>Hozircha top donaterlar yo'q.</b>\n\nBirinchi bo'lishingiz mumkin!"
    else:
        lines = ["🏆 <b>Top 10 Donaterlar:</b>\n", "━━━━━━━━━━━━━━━━━━━━"]
        for i, user in enumerate(tops, 1):
            nick = user['mc_nickname'] or "Nickname yo'q"
            lines.append(f"{i}. <b>{nick}</b> — <code>{fmt_price(user['total_spent'])}</code>")
        text = "\n".join(lines)

    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb.back_home())
    await call.answer()

# ──────────────────────────────────────────────────────────────────────────────
# User Ticket Flow
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "support_ticket")
async def cb_support_ticket(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SupportState.waiting_for_ticket)
    await call.message.edit_text(
        "✍️ <b>Adminga xabar yozing</b>\n\n"
        "Muammo yoki savolingizni batafsil tushuntiring.",
        parse_mode="HTML",
        reply_markup=kb.back_home()
    )
    await call.answer()

@router.message(SupportState.waiting_for_ticket)
async def process_ticket(message: Message, state: FSMContext, bot: Bot) -> None:
    if not config.admin_chat_id:
        await message.answer("⚠️ Tizimda xatolik: Admin guruhi sozlanmagan.")
        return

    user_info = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
    ticket_text = (
        f"📩 <b>Yangi murojaat!</b>\n"
        f"👤 Kimdan: {user_info} (ID: <code>{message.from_user.id}</code>)\n"
        f"🎮 Nickname: <b>{message.text[:50]}...</b>\n\n"
        f"📝 Xabar:\n{message.text}"
    )

    await bot.send_message(
        chat_id=config.admin_chat_id,
        text=ticket_text,
        parse_mode="HTML",
        reply_markup=kb.support_reply_markup(message.from_user.id)
    )
    
    await state.clear()
    await message.answer("✅ Xabaringiz yuborildi. Tez orada javob qaytaramiz!", reply_markup=kb.main_menu())

# ──────────────────────────────────────────────────────────────────────────────
# Admin Reply from Group (Handling Reply mechanism)
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin:reply_ticket:"))
async def cb_admin_reply_ticket(call: CallbackQuery, state: FSMContext) -> None:
    user_id = int(call.data.split(":")[2])
    await state.set_state(SupportState.waiting_for_admin_reply)
    await state.update_data(reply_to_user_id=user_id)
    await call.message.reply(f"✍️ ID: <code>{user_id}</code> ga javobingizni yozing:", parse_mode="HTML")
    await call.answer()

@router.message(SupportState.waiting_for_admin_reply, F.chat.id == config.admin_chat_id)
async def admin_send_reply(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    user_id = data.get("reply_to_user_id")
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"📨 <b>Admin xabari:</b>\n\n{message.text}",
            parse_mode="HTML",
            reply_markup=kb.main_menu()
        )
        await message.reply("✅ Javob foydalanuvchiga yuborildi.")
    except Exception as e:
        await message.reply(f"❌ Yuborishda xatolik: {e}")
    
    await state.clear()