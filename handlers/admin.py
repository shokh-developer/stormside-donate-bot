"""
handlers/admin.py – admin panel: view orders, approve/reject.
"""
from __future__ import annotations

import logging
import asyncio
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from config import config
from db import repository as repo
from keyboards import keyboards as kb
from middlewares.admin import admin_required
from services.order_service import deliver_order, reject_order
from services.rcon_service import rcon
from utils.helpers import admin_order_text, fmt_price

logger = logging.getLogger(__name__)
router = Router(name="admin")


class AdminRejectForm(StatesGroup):
    waiting_custom_reason = State()

class AdminProductForm(StatesGroup):
    waiting_for_price = State()

class AdminPromoForm(StatesGroup):
    waiting_for_code = State()
    waiting_for_percent = State()

class AdminNewsForm(StatesGroup):
    waiting_for_news = State()

class AdminKillForm(StatesGroup):
    waiting_for_nickname = State()

class AdminAddProductForm(StatesGroup):
    waiting_for_category = State()
    waiting_for_name = State()
    waiting_for_emoji = State()
    waiting_for_price = State()
    waiting_for_extra = State() # LP group for ranks, amount for coins

class AdminAddForm(StatesGroup):
    waiting_for_id = State()


# ──────────────────────────────────────────────────────────────────────────────
# /admin command
# ──────────────────────────────────────────────────────────────────────────────

@router.message(Command("admin", "adminpanel"))
@admin_required
async def cmd_admin(message: Message, state: FSMContext) -> None:
    await state.clear()
    pending = await repo.get_pending_orders()
    await message.answer(
        f"🔐 <b>Admin Panel</b>\n\n"
        f"📋 Pending orders: <b>{len(pending)}</b>\n"
        f"👤 Admin: <b>{message.from_user.full_name}</b>",
        parse_mode="HTML",
        reply_markup=kb.admin_main(),
    )


@router.callback_query(F.data == "admin:main_panel")
@admin_required
async def cb_admin_main(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    pending = await repo.get_pending_orders()
    text = (
        f"🔐 <b>Admin Panel</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 Kutilayotgan: <b>{len(pending)} ta</b>\n"
        f"👤 Admin: <b>{call.from_user.full_name}</b>"
    )
    
    if call.message.photo:
        await call.message.delete()
        await call.message.answer(text, parse_mode="HTML", reply_markup=kb.admin_main())
    else:
        try:
            await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb.admin_main())
        except Exception:
            await call.message.answer(text, parse_mode="HTML", reply_markup=kb.admin_main())
            await call.message.delete()
    await call.answer()


# ──────────────────────────────────────────────────────────────────────────────
# Add Admin
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:add_new")
@admin_required
async def cb_admin_add_start(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminAddForm.waiting_for_id)
    await call.message.edit_text(
        "👤 <b>Yangi admin qo'shish</b>\n\n"
        "Yangi adminning Telegram ID raqamini yuboring.\n"
        "ID raqamni @userinfobot orqali bilib olish mumkin.\n\n"
        "Bekor qilish uchun /cancel deb yozing.",
        parse_mode="HTML",
        reply_markup=kb.back_button("admin:main_panel")
    )
    await call.answer()

@router.message(AdminAddForm.waiting_for_id)
@admin_required
async def process_add_admin(message: Message, state: FSMContext) -> None:
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=kb.admin_main())
        return

    if not message.text or not message.text.isdigit():
        await message.answer("❌ Iltimos, faqat raqamli ID kiriting!")
        return

    new_id = int(message.text)
    success = config.add_admin(new_id)
    
    await state.clear()
    if success:
        await message.answer(f"✅ ID <code>{new_id}</code> muvaffaqiyatli adminlar ro'yxatiga va <code>.env</code> fayliga qo'shildi!", parse_mode="HTML", reply_markup=kb.admin_main())
    else:
        await message.answer(f"⚠️ Bu ID (<code>{new_id}</code>) allaqachon adminlar ro'yxatida mavjud.", parse_mode="HTML", reply_markup=kb.admin_main())


# ──────────────────────────────────────────────────────────────────────────────
# Promo Management
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:promos")
@admin_required
async def cb_admin_promos(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    promos = await repo.get_all_promos() # Assuming this method exists in repository
    await call.message.edit_text(
        "🎁 <b>Promo-kodlar boshqaruvi</b>\n\nO'chirish uchun kod ustiga bosing:",
        parse_mode="HTML",
        reply_markup=kb.admin_promo_list(promos)
    )
    await call.answer()

@router.callback_query(F.data == "admin:add_promo")
@admin_required
async def cb_add_promo_start(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminPromoForm.waiting_for_code)
    await call.message.edit_text("🎟 Yangi promo-kod nomini kiriting:")
    await call.answer()

@router.message(AdminPromoForm.waiting_for_code)
@admin_required
async def receive_promo_code(message: Message, state: FSMContext) -> None:
    await state.update_data(code=message.text.strip().upper())
    await state.set_state(AdminPromoForm.waiting_for_percent)
    await message.answer("🔢 Necha foiz chegirma beradi? (faqat raqam, masalan: 20):")

@router.message(AdminPromoForm.waiting_for_percent)
@admin_required
async def receive_promo_percent(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.isdigit():
        await message.answer("❌ Iltimos, raqam kiriting!")
        return
    
    percent = int(message.text)
    if not (0 <= percent <= 100):
        await message.answer("❌ Foiz 0 va 100 orasida bo'lishi kerak!")
        return

    data = await state.get_data()
    await repo.add_promo(data['code'], percent) # Assuming this method exists
    await state.clear()
    await message.answer(
        f"✅ Promo-kod yaratildi: <b>{data['code']}</b>\nChegirma: <b>{percent}%</b>",
        parse_mode="HTML",
        reply_markup=kb.admin_main()
    )

@router.callback_query(F.data.startswith("admin:del_promo:"))
@admin_required
async def cb_del_promo(call: CallbackQuery) -> None:
    promo_id = int(call.data.split(":")[2])
    await repo.delete_promo(promo_id) # Assuming this method exists
    await call.answer("Promo-kod o'chirildi!")
    await cb_admin_promos(call)


# ──────────────────────────────────────────────────────────────────────────────
# News Broadcasting
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:news")
@admin_required
async def cb_admin_news(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminNewsForm.waiting_for_news)
    await call.message.edit_text(
        "📢 <b>Yangilik yuborish</b>\n\n"
        "Barcha foydalanuvchilarga yuboriladigan xabarni yozing. "
        "Matn, rasm yoki video yuborishingiz mumkin.\n\n"
        "Bekor qilish uchun /cancel deb yozing.",
        parse_mode="HTML",
        reply_markup=kb.back_button("admin:main_panel")
    )
    await call.answer()

@router.message(AdminNewsForm.waiting_for_news)
@admin_required
async def process_news_broadcast(message: Message, state: FSMContext, bot: Bot) -> None:
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=kb.admin_main())
        return

    users = await repo.get_all_users()
    await state.clear()
    
    sent_count = 0
    error_count = 0
    status_msg = await message.answer(f"⏳ Yuborilmoqda: 0/{len(users)}...")

    for user in users:
        try:
            await message.copy_to(chat_id=user['telegram_id'])
            sent_count += 1
            if sent_count % 10 == 0:
                await status_msg.edit_text(f"⏳ Yuborilmoqda: {sent_count}/{len(users)}...")
            await asyncio.sleep(0.05) # Telegram limitlaridan himoya
        except Exception:
            error_count += 1

    await status_msg.edit_text(
        f"✅ <b>Yangilik barcha foydalanuvchilarga yuborildi!</b>\n\n"
        f"👥 Jami: {len(users)}\n"
        f"✅ Yuborildi: {sent_count}\n"
        f"❌ Xatolik: {error_count}",
        parse_mode="HTML",
        reply_markup=kb.admin_main()
    )

# ──────────────────────────────────────────────────────────────────────────────
# Admin callbacks
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:pending")
@admin_required
async def cb_admin_pending(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    orders = await repo.get_pending_orders()
    text = "📋 <b>Kutilayotgan buyurtmalar</b>\n━━━━━━━━━━━━━━━━━━━━\nBirini tanlang:"
    
    if not orders:
        text = "✅ <b>Barcha buyurtmalar bajarilgan!</b>"
        markup = kb.admin_main()
    else:
        markup = kb.admin_pending_list(orders)

    if call.message.photo:
        await call.message.delete()
        await call.message.answer(text, parse_mode="HTML", reply_markup=markup)
    else:
        try:
            await call.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
        except Exception:
            await call.message.answer(text, parse_mode="HTML", reply_markup=markup)
            await call.message.delete()
            
    await call.answer()


@router.callback_query(F.data.startswith("admin:order:"))
@admin_required
async def cb_admin_order_detail(call: CallbackQuery, bot: Bot) -> None:
    order_id = int(call.data.split(":")[2])
    order = await repo.get_order(order_id)

    if not order:
        await call.answer("Order not found.", show_alert=True)
        return

    text = admin_order_text(order)

    if order.get("screenshot_file_id"):
        try:
            await call.message.answer_photo(
                photo=order["screenshot_file_id"],
                caption=text,
                parse_mode="HTML",
                reply_markup=kb.admin_order_actions(order_id),
            )
            await call.message.delete()
        except Exception:
            await call.message.edit_text(
                text, parse_mode="HTML",
                reply_markup=kb.admin_order_actions(order_id),
            )
    else:
        await call.message.edit_text(
            text + "\n\n⚠️ <i>No screenshot attached</i>",
            parse_mode="HTML",
            reply_markup=kb.admin_order_actions(order_id),
        )
    await call.answer()


# ──────────────────────────────────────────────────────────────────────────────
# Approve
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin:approve:"))
@admin_required
async def cb_admin_approve(call: CallbackQuery, bot: Bot) -> None:
    order_id = int(call.data.split(":")[2])
    admin_id = call.from_user.id

    await call.answer("⏳ Processing...", show_alert=False)

    ok, result = await deliver_order(order_id, admin_id)
    order = await repo.get_order(order_id)

    if ok:
        status_msg = (
            f"✅ <b>Order #{order_id} Approved & Delivered!</b>\n\n"
            f"🎮 Nickname: <b>{order['mc_nickname']}</b>\n"
            f"🏅 Product: <b>{order['product_name']}</b>\n\n"
            f"📡 RCON: <code>{result}</code>"
        )
        # Notify the user
        await _notify_user(
            bot,
            order["telegram_id"],
            f"🎉 <b>Your order has been approved!</b>\n\n"
            f"{order.get('emoji','🎮')} <b>{order['product_name']}</b> has been delivered\n"
            f"to your account <b>{order['mc_nickname']}</b>.\n\n"
            f"Thank you for supporting Stormside! ⛏",
        )
    else:
        status_msg = (
            f"⚠️ <b>Order #{order_id} – RCON Failed</b>\n\n"
            f"Payment approved but delivery failed:\n"
            f"<code>{result}</code>\n\n"
            f"Please deliver manually."
        )

    try:
        await call.message.edit_caption(status_msg, parse_mode="HTML")
    except Exception:
        try:
            await call.message.edit_text(status_msg, parse_mode="HTML")
        except Exception:
            await call.message.answer(status_msg, parse_mode="HTML")


# ──────────────────────────────────────────────────────────────────────────────
# Reject
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin:reject:"))
@admin_required
async def cb_admin_reject(call: CallbackQuery) -> None:
    order_id = int(call.data.split(":")[2])
    await call.message.edit_reply_markup(
        reply_markup=kb.admin_reject_reason(order_id)
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin:reject_reason:"))
@admin_required
async def cb_admin_reject_reason(call: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    parts = call.data.split(":")
    order_id = int(parts[2])
    reason_key = parts[3]

    reasons = {
        "duplicate": "Duplicate payment detected.",
        "invalid_screenshot": "Invalid or unclear screenshot.",
        "other": None,  # will ask for custom reason
    }

    reason = reasons.get(reason_key)

    if reason_key == "other":
        await state.set_state(AdminRejectForm.waiting_custom_reason)
        await state.update_data(order_id=order_id)
        await call.message.answer(
            f"✏️ Enter rejection reason for order <b>#{order_id}</b>:",
            parse_mode="HTML",
        )
        await call.answer()
        return

    await _do_reject(call, bot, order_id, reason or "Rejected by admin.")


@router.message(AdminRejectForm.waiting_custom_reason)
@admin_required
async def receive_reject_reason(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    order_id = data.get("order_id")
    reason = message.text or "Rejected by admin."
    await state.clear()

    # Create a fake CallbackQuery-like context
    order = await repo.get_order(order_id)
    success = await reject_order(order_id, message.from_user.id, reason)

    if success and order:
        await _notify_user(
            bot,
            order["telegram_id"],
            f"❌ <b>Order #{order_id} was rejected.</b>\n\n"
            f"Reason: {reason}\n\n"
            f"If you believe this is an error, contact {config.support_handle}.",
        )
        await message.answer(
            f"✅ Order #{order_id} rejected.\nReason: {reason}",
            reply_markup=kb.admin_main(),
        )
    else:
        await message.answer("❌ Failed to reject order.", reply_markup=kb.admin_main())


async def _do_reject(call: CallbackQuery, bot: Bot, order_id: int, reason: str) -> None:
    order = await repo.get_order(order_id)
    success = await reject_order(order_id, call.from_user.id, reason)

    if success and order:
        await _notify_user(
            bot,
            order["telegram_id"],
            f"❌ <b>Order #{order_id} was rejected.</b>\n\n"
            f"Reason: {reason}\n\n"
            f"If you believe this is an error, contact {config.support_handle}.",
        )
        status_msg = f"✅ Order #{order_id} rejected.\nReason: {reason}"
    else:
        status_msg = "❌ Failed to reject order."

    try:
        await call.message.edit_caption(status_msg, parse_mode="HTML")
    except Exception:
        try:
            await call.message.edit_text(status_msg, parse_mode="HTML")
        except Exception:
            await call.message.answer(status_msg, parse_mode="HTML")

    await call.answer()


# ──────────────────────────────────────────────────────────────────────────────
# Product Management
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:products")
@admin_required
async def cb_admin_products(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    products = await repo.get_all_products()
    await call.message.edit_text(
        "📦 <b>Mahsulotlarni boshqarish</b>\n\n"
        "Tahrirlash uchun mahsulotni tanlang:",
        parse_mode="HTML",
        reply_markup=kb.admin_products_list(products),
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin:edit_prod:"))
@admin_required
async def cb_admin_edit_product(call: CallbackQuery) -> None:
    product_id = int(call.data.split(":")[2])
    product = await repo.get_product(product_id)
    
    if not product:
        await call.answer("Mahsulot topilmadi.", show_alert=True)
        return

    status = "Faol ✅" if product['is_active'] else "O'chirilgan ❌"
    from utils.helpers import product_card
    text = (
        f"🛠 <b>Mahsulotni tahrirlash</b>\n\n"
        f"{product_card(product)}\n"
        f"Holati: <b>{status}</b>"
    )
    
    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.admin_product_edit(product_id, bool(product['is_active'])),
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin:toggle_prod:"))
@admin_required
async def cb_admin_toggle_product(call: CallbackQuery) -> None:
    _, _, pid, status = call.data.split(":")
    await repo.toggle_product_status(int(pid), bool(int(status)))
    await call.answer("Mahsulot holati yangilandi!")
    # Refresh the view
    call.data = f"admin:edit_prod:{pid}"
    await cb_admin_edit_product(call)


@router.callback_query(F.data.startswith("admin:set_price:"))
@admin_required
async def cb_admin_set_price(call: CallbackQuery, state: FSMContext) -> None:
    product_id = int(call.data.split(":")[2])
    await state.set_state(AdminProductForm.waiting_for_price)
    await state.update_data(product_id=product_id)
    await call.message.answer("💰 Yangi narxni kiriting (faqat raqam):")
    await call.answer()


@router.message(AdminProductForm.waiting_for_price)
@admin_required
async def receive_new_price(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.isdigit():
        await message.answer("❌ Iltimos, faqat raqam kiriting!")
        return

    new_price = float(message.text)
    data = await state.get_data()
    product_id = data['product_id']
    
    await repo.update_product_price(product_id, new_price)
    await state.clear()
    await message.answer(
        f"✅ Narx muvaffaqiyatli <b>{int(new_price):,} UZS</b> ga o'zgartirildi.",
        parse_mode="HTML",
        reply_markup=kb.admin_main(),
    )


@router.callback_query(F.data == "admin:add_product")
@admin_required
async def cb_admin_add_start(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminAddProductForm.waiting_for_category)
    await call.message.edit_text(
        "📂 <b>Kategoriyani tanlang:</b>",
        parse_mode="HTML",
        reply_markup=kb.admin_category_selector()
    )
    await call.answer()


@router.callback_query(AdminAddProductForm.waiting_for_category, F.data.startswith("admin:set_cat:"))
@admin_required
async def receive_category(call: CallbackQuery, state: FSMContext) -> None:
    category = call.data.split(":")[2]
    await state.update_data(category=category)
    await state.set_state(AdminAddProductForm.waiting_for_name)
    await call.message.edit_text("📝 Mahsulot nomini kiriting (masalan: <i>VIP</i> yoki <i>1000 Coins</i>):", parse_mode="HTML")
    await call.answer()


@router.message(AdminAddProductForm.waiting_for_name)
@admin_required
async def receive_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text)
    await state.set_state(AdminAddProductForm.waiting_for_emoji)
    await message.answer("🎨 Mahsulot uchun emoji kiriting (masalan: ⚔️):")


@router.message(AdminAddProductForm.waiting_for_emoji)
@admin_required
async def receive_emoji(message: Message, state: FSMContext) -> None:
    await state.update_data(emoji=message.text)
    await state.set_state(AdminAddProductForm.waiting_for_price)
    await message.answer("💰 Narxini kiriting (faqat raqam, masalan: 5000):")


@router.message(AdminAddProductForm.waiting_for_price)
@admin_required
async def receive_price(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.isdigit():
        await message.answer("❌ Iltimos, faqat raqam kiriting!")
        return
    
    await state.update_data(price=float(message.text))
    data = await state.get_data()
    
    await state.set_state(AdminAddProductForm.waiting_for_extra)
    if data['category'] == 'rank':
        await message.answer("🔑 LuckPerms guruh nomini kiriting (masalan: <i>vip</i>):", parse_mode="HTML")
    else:
        await message.answer("🪙 Tanga miqdorini kiriting (faqat raqam):")


@router.message(AdminAddProductForm.waiting_for_extra)
@admin_required
async def receive_extra(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    category = data['category']
    
    lp_group = None
    coins_amount = None
    duration_days = 0
    
    if category == 'rank':
        lp_group = message.text.strip().lower()
        duration_days = 30  # Default 30 days for ranks
    else:
        if not message.text or not message.text.isdigit():
            await message.answer("❌ Iltimos, miqdorni raqamda kiriting!")
            return
        coins_amount = int(message.text)

    # Save to database
    await repo.add_product(
        name=data['name'],
        category=category,
        price=data['price'],
        emoji=data['emoji'],
        lp_group=lp_group,
        coins_amount=coins_amount,
        duration_days=duration_days
    )
    
    await state.clear()
    await message.answer(
        f"✅ <b>Yangi mahsulot qo'shildi!</b>\n\n"
        f"Nomi: {data['emoji']} {data['name']}\n"
        f"Kategoriya: {category.capitalize()}\n"
        f"Narxi: {int(data['price']):,} UZS",
        parse_mode="HTML",
        reply_markup=kb.admin_main()
    )


@router.callback_query(F.data.startswith("admin:revoke:"))
@admin_required
async def cb_admin_revoke(call: CallbackQuery, bot: Bot) -> None:
    order_id = int(call.data.split(":")[2])
    order = await repo.get_order(order_id)

    if not order:
        await call.answer("Buyurtma topilmadi.", show_alert=True)
        return

    await call.answer("🔄 Mahsulot olib qo'yilmoqda...", show_alert=False)

    # 1. Determine RCON command to revoke
    if order['category'] == 'rank':
        # LuckPerms: remove parent group
        rcon_cmd = f"lp user {order['mc_nickname']} parent remove {order['lp_group']}"
    else:
        # Coins: remove amount (assuming EssentialsX or similar)
        rcon_cmd = f"eco take {order['mc_nickname']} {order['coins_amount']}"

    # 2. Execute RCON
    _, rcon_result = await rcon.send_command(rcon_cmd)
    
    # 3. Update database status
    await repo.update_order_status(
        order_id, 
        status="rejected", 
        admin_id=call.from_user.id,
        admin_note="Mahsulot admin tomonidan olib qo'yildi (Revoked)",
        rcon_command=f"REVOKE: {rcon_cmd}",
        rcon_result=rcon_result
    )

    # 4. Notify user
    await _notify_user(
        bot,
        order["telegram_id"],
        f"⚠️ <b>Buyurtma bekor qilindi!</b>\n\n"
        f"Sizning <b>#{order_id}</b> raqamli buyurtmangiz admin tomonidan bekor qilindi "
        f"va berilgan mahsulotlar olib qo'yildi.\n\n"
        f"Sabab: Sohta chek yoki xato to'lov."
    )

    status_msg = (
        f"🗑 <b>Order #{order_id} olib qo'yildi!</b>\n"
        f"Foydalanuvchi: <code>{order['mc_nickname']}</code>\n"
        f"RCON Natijasi: <code>{rcon_result}</code>"
    )
    
    try:
        await call.message.edit_caption(caption=status_msg, parse_mode="HTML")
    except Exception:
        await call.message.answer(status_msg, parse_mode="HTML")

# ──────────────────────────────────────────────────────────────────────────────
# Kill Player Logic
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:kill_player")
@admin_required
async def cb_admin_kill_start(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminKillForm.waiting_for_nickname)
    await call.message.edit_text("💀 O'yinchini o'ldirish (kill) uchun nickname yozing:")
    await call.answer()

@router.message(AdminKillForm.waiting_for_nickname)
@admin_required
async def receive_kill_nickname(message: Message, state: FSMContext) -> None:
    nickname = message.text.strip()
    await state.clear()
    ok, result = await rcon.send_command(f"kill {nickname}")
    await message.answer(f"RCON Natijasi: <code>{result}</code>", parse_mode="HTML", reply_markup=kb.admin_main())

# ──────────────────────────────────────────────────────────────────────────────
# Rank Setup Command
# ──────────────────────────────────────────────────────────────────────────────

@router.message(Command("setup_ranks"))
@admin_required
async def cmd_setup_ranks(message: Message) -> None:
    """Bazani yangi ranklar bilan to'ldiradi."""
    new_ranks = [
        ("ECLIPSE", "🌑", 5000, 30, "eclipse"), ("ECLIPSE", "🌑", 20000, 0, "eclipse"),
        ("PHOENIX", "🛡", 8000, 30, "phoenix"), ("PHOENIX", "🛡", 30000, 0, "phoenix"),
        ("ORACLE", "🪙", 12000, 30, "oracle"), ("ORACLE", "🪙", 45000, 0, "oracle"),
        ("VOYAGER", "⚒️", 18000, 30, "voyager"), ("VOYAGER", "⚒️", 60000, 0, "voyager"),
        ("CATALYST", "🔪", 25000, 30, "catalyst"), ("CATALYST", "🔪", 80000, 0, "catalyst"),
        ("CELESTIAL", "💎", 35000, 30, "celestial"), ("CELESTIAL", "💎", 110000, 0, "celestial"),
        ("AURORA", "⚡️", 45000, 30, "aurora"), ("AURORA", "⚡️", 145000, 0, "aurora"),
        ("IMMORTAL", "⚡️➕", 55000, 30, "immortal"), ("IMMORTAL", "⚡️➕", 190000, 0, "immortal"),
        ("APEX", "🌟", 70000, 30, "apex"), ("APEX", "🌟", 250000, 0, "apex"),
        ("LUMINARY", "🤩", 90000, 30, "luminary"), ("LUMINARY", "🤩", 320000, 0, "luminary"),
        ("GREAT", "👑", 110000, 30, "great"), ("GREAT", "👑", 400000, 0, "great"),
    ]

    try:
        # Yangi ranklarni qo'shish
        count = 0
        for name, emoji, price, days, lp in new_ranks:
            duration_text = " (1 oy)" if days == 30 else " (Butunlay)"
            await repo.add_product(
                name=f"{name}{duration_text}",
                category="rank",
                price=float(price),
                emoji=emoji,
                lp_group=lp,
                coins_amount=None,
                duration_days=days
            )
            count += 1

        await message.answer(
            f"✅ <b>Ranklar muvaffaqiyatli qo'shildi!</b>\n\n"
            f"Jami {count} ta variant yaratildi.\n\n"
            f"⚠️ <i>Eslatma: Do'kondagi eski ranklarni o'chirib tashlashni unutmang.</i>",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Setup ranks failed: {e}")
        await message.answer(f"❌ Xatolik yuz berdi: {e}")

# ──────────────────────────────────────────────────────────────────────────────
# RCON test
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:rcon_test")
@admin_required
async def cb_rcon_test(call: CallbackQuery) -> None:
    await call.answer("Testing RCON connection...", show_alert=False)
    ok, result = await rcon.send_command("list")
    status = "✅ Connected" if ok else f"❌ Error: {result}"
    host = f"{config.rcon_host}:{config.rcon_port}"

    await call.message.edit_text(
        f"🔌 <b>RCON Status</b>\n\n"
        f"Host: <code>{host}</code>\n"
        f"Status: {status}\n\n"
        f"🕒 Oxirgi tekshiruv: <code>{datetime.now().strftime('%H:%M:%S')}</code>",
        parse_mode="HTML",
        reply_markup=kb.admin_main(),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Internal: DM user about order update
# ──────────────────────────────────────────────────────────────────────────────

async def _notify_user(bot: Bot, telegram_id: int, text: str) -> None:
    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=text,
            parse_mode="HTML",
            reply_markup=kb.main_menu(),
        )
    except Exception:
        logger.warning("Could not notify user %s", telegram_id)
