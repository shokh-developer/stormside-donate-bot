"""
handlers/payment.py – QR display, screenshot capture, order creation.
"""
from __future__ import annotations

import logging
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, Message

from config import config
from db import repository as repo
from keyboards import keyboards as kb
from utils.helpers import qr_instructions, fmt_price

logger = logging.getLogger(__name__)
router = Router(name="payment")


class PaymentForm(StatesGroup):
    waiting_screenshot = State()


# ──────────────────────────────────────────────────────────────────────────────
# Show QR / payment details
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pay:"))
async def cb_pay(call: CallbackQuery, state: FSMContext, db_user: dict) -> None:
    parts = call.data.split(":")
    method = parts[1]
    product_id = int(parts[2])

    product = await repo.get_product(product_id)
    if not product:
        await call.answer("Mahsulot topilmadi.", show_alert=True)
        return

    # Promo-kod orqali kelgan narxni tekshirish, aks holda mahsulot narxi
    amount = float(parts[3]) if len(parts) > 3 else product["price"]

    # Create order (pending, no screenshot yet)
    order_id = await repo.create_order(
        telegram_id=call.from_user.id,
        product_id=product_id,
        mc_nickname=db_user["mc_nickname"],
        amount=amount,
        payment_method=method,
    )

    card = config.click_card if method == "click" else config.payme_card
    qr_path = config.click_qr_path if method == "click" else config.payme_qr_path

    instructions = qr_instructions(
        method=method,
        amount=amount,
        card=card,
        holder=config.card_holder,
        order_id=order_id,
    )

    # Try to send QR image
    qr_file = Path(qr_path)
    try:
        if qr_file.exists():
            await call.message.answer_photo(
                photo=FSInputFile(qr_path),
                caption=instructions,
                parse_mode="HTML",
                reply_markup=kb.after_qr(order_id),
            )
            await call.message.delete()
        else:
            # No QR image available – send text only
            await call.message.edit_text(
                instructions,
                parse_mode="HTML",
                reply_markup=kb.after_qr(order_id),
            )
    except Exception:
        logger.exception("Failed to send QR image for order %s", order_id)
        await call.message.edit_text(
            instructions,
            parse_mode="HTML",
            reply_markup=kb.after_qr(order_id),
        )

    await call.answer()


# ──────────────────────────────────────────────────────────────────────────────
# Await screenshot
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("await_screenshot:"))
async def cb_await_screenshot(call: CallbackQuery, state: FSMContext) -> None:
    order_id = int(call.data.split(":")[1])

    # Verify order belongs to this user
    order = await repo.get_order(order_id)
    if not order or order["telegram_id"] != call.from_user.id:
        await call.answer("Buyurtma topilmadi.", show_alert=True)
        return

    if order["status"] != "pending":
        await call.answer(
            f"Ushbu buyurtma holati: {order['status']}.", show_alert=True
        )
        return

    await state.set_state(PaymentForm.waiting_screenshot)
    await state.update_data(order_id=order_id)

    await call.message.answer(
        "📸 <b>To'lov chekini yuboring</b>\n\n"
        f"Buyurtma: <b>#{order_id}</b>\n\n"
        "Iltimos, to'lov muvaffaqiyatli bajarilganini tasdiqlovchi <b>rasmni</b> yuboring.\n"
        "Rasmda summa va tranzaksiya ID si ko'rinishi shart.",
        parse_mode="HTML",
        reply_markup=kb.back_home(),
    )
    await call.answer()


@router.message(PaymentForm.waiting_screenshot, F.photo)
async def receive_screenshot(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    order_id = data.get("order_id")
    if not order_id:
        await state.clear()
        return

    order = await repo.get_order(order_id)
    if not order or order["telegram_id"] != message.from_user.id:
        await state.clear()
        await message.answer("❌ Buyurtma topilmadi.", reply_markup=kb.main_menu())
        return

    # Get the largest photo (last = highest quality)
    file_id = message.photo[-1].file_id

    # Save screenshot file_id via repository
    await repo.update_order_screenshot(order_id, file_id)

    await state.clear()
    await message.answer(
        f"✅ <b>Chek qabul qilindi!</b>\n\n"
        f"Buyurtma <b>#{order_id}</b> hozir ko'rib chiqilmoqda.\n\n"
        f"⏱ Adminlar yaqin orada to'lovni tekshirib tasdiqlashadi.\n"
        f"Jarayon yakunlangach sizga xabar yuboramiz.",
        parse_mode="HTML",
        reply_markup=kb.main_menu(),
    )

    # Notify admins
    await _notify_admins(bot, order_id, file_id)


@router.message(PaymentForm.waiting_screenshot)
async def screenshot_not_photo(message: Message) -> None:
    await message.answer(
        "❌ Iltimos, fayl yoki matn emas, <b>rasm</b> (screenshot) yuboring.",
        parse_mode="HTML",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Cancel order
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cancel_order:"))
async def cb_cancel_order(call: CallbackQuery) -> None:
    order_id = int(call.data.split(":")[1])
    await call.message.edit_text(
        f"❓ Haqiqatan ham <b>#{order_id}</b>-sonli buyurtmani bekor qilmoqchimisiz?",
        parse_mode="HTML",
        reply_markup=kb.cancel_order_confirm(order_id),
    )
    await call.answer()


@router.callback_query(F.data.startswith("do_cancel:"))
async def cb_do_cancel(call: CallbackQuery, state: FSMContext) -> None:
    order_id = int(call.data.split(":")[1])
    order = await repo.get_order(order_id)

    if not order or order["telegram_id"] != call.from_user.id:
        await call.answer("Buyurtma topilmadi.", show_alert=True)
        return

    if order["status"] != "pending":
        await call.answer("Ushbu bosqichda buyurtmani bekor qilib bo'lmaydi.", show_alert=True)
        return

    await repo.update_order_status(order_id, "rejected", admin_note="Foydalanuvchi tomonidan bekor qilindi")
    await state.clear()

    await call.message.edit_text(
        f"✅ Buyurtma <b>#{order_id}</b> bekor qilindi.",
        parse_mode="HTML",
        reply_markup=kb.main_menu(),
    )
    await call.answer()


# ──────────────────────────────────────────────────────────────────────────────
# Internal: notify admins of new order
# ──────────────────────────────────────────────────────────────────────────────

async def _notify_admins(bot: Bot, order_id: int, screenshot_file_id: str) -> None:
    order = await repo.get_order(order_id)
    if not order:
        return

    from utils.helpers import admin_order_text
    text = admin_order_text(order)

    targets = list(config.admin_ids)
    if config.admin_chat_id and config.admin_chat_id not in targets:
        targets.append(config.admin_chat_id)

    for admin_id in targets:
        try:
            await bot.send_photo(
                chat_id=admin_id,
                photo=screenshot_file_id, # No change here, "Stromeside" is not in this file.
                caption=text,
                parse_mode="HTML",
                reply_markup=kb.admin_order_actions(order_id),
            )
        except Exception:
            logger.exception("Failed to notify admin %s for order %s", admin_id, order_id)
