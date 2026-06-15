"""
handlers/shop.py – browse products and initiate purchases.
"""
from __future__ import annotations

import logging
from typing import Optional, Any

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from db import repository as repo
from keyboards import keyboards as kb
from utils.helpers import product_card
from services.order_service import deliver_order
from config import config

logger = logging.getLogger(__name__)
router = Router(name="shop")

class PromoState(StatesGroup):
    waiting_for_promo = State()


@router.message(F.text == "🛒 Do'kon")
async def msg_shop_main(message: Message) -> None:
    await message.answer(
        "🛒 <b>Stormside Do'koni</b>\n\n"
        "Bugun nima sotib olishni xohlaysiz?\n\n"
        "⚔️ <b>Ranklar</b> — Serverda doimiy imtiyozlarni oching\n"
        "🤑 <b>SIDE (Vales)</b> — O'yin ichidagi valyuta paketlari",
        parse_mode="HTML",
        reply_markup=kb.shop_categories(),
    )


@router.callback_query(F.data == "shop:main")
async def cb_shop_main(call: CallbackQuery) -> None:
    await call.message.edit_text(
        "🛒 <b>Stormside Do'koni</b>\n\n"
        "Bugun nima sotib olishni xohlaysiz?\n\n"
        "⚔️ <b>Ranklar</b> — Serverda doimiy imtiyozlarni oching\n"
        "🤑 <b>SIDE (Vales)</b> — O'yin ichidagi valyuta paketlari",
        parse_mode="HTML",
        reply_markup=kb.shop_categories(),
    )
    await call.answer()


@router.callback_query(F.data == "shop:ranks")
async def cb_shop_ranks(call: CallbackQuery) -> None:
    products = await repo.get_products(category="rank")
    seen: dict = {}
    grouped = []
    for p in products:
        key = p["lp_group"]
        if key not in seen:
            seen[key] = True
            grouped.append({
                "emoji": p["emoji"],
                "name": p["name"].split(" (")[0],
                "lp_group": key,
            })
    await call.message.edit_text(
        "⚔️ <b>Ranklar Do'koni</b>\n\n"
        "Qaysi rankni olmoqchisiz? Tanlang:",
        parse_mode="HTML",
        reply_markup=kb.rank_list(grouped),
    )
    await call.answer()


@router.callback_query(F.data.startswith("rank:"))
async def cb_rank_select(call: CallbackQuery) -> None:
    lp_group = call.data.split(":")[1]
    products = await repo.get_products(category="rank")
    monthly = next((p for p in products if p["lp_group"] == lp_group and p["duration_days"] == 30), None)
    permanent = next((p for p in products if p["lp_group"] == lp_group and p["duration_days"] == 0), None)

    if not monthly or not permanent:
        await call.answer("Mahsulot topilmadi.", show_alert=True)
        return

    rank_name = monthly["name"].split(" (")[0]
    rank_emoji = monthly["emoji"]

    await call.message.edit_text(
        f"{rank_emoji} <b>{rank_name}</b>\n\n"
        f"⏳ <b>1 Oy</b> — {int(monthly['price']):,} UZS\n"
        f"♾️ <b>Butunlay</b> — {int(permanent['price']):,} UZS\n\n"
        f"Qaysi variantni tanlaysiz?",
        parse_mode="HTML",
        reply_markup=kb.rank_duration(monthly, permanent),
    )
    await call.answer()


@router.callback_query(F.data == "shop:coins")
async def cb_shop_coins(call: CallbackQuery) -> None:
    products = await repo.get_products(category="coins")
    await call.message.edit_text(
        "🤑 <b>SIDE — O'yin ichidagi valyuta</b>\n\n"
        "Vales orqali buyumlar sotib olish, yangi imkoniyatlarni ochish\n"
        "va boshqa o'yinchilar bilan savdo qilish mumkin.",
        parse_mode="HTML",
        reply_markup=kb.product_list(products, "coins"),
    )
    await call.answer()


@router.callback_query(F.data == "shop:cases")
async def cb_shop_cases(call: CallbackQuery) -> None:
    products = await repo.get_products(category="case")
    await call.message.edit_text(
        "🎁 <b>Case'lar</b>\n\n"
        "Case'lar ichida maxsus mukofotlar, tokenlar va asbob-uskunalar mavjud.\n"
        "Omadingizni sinab ko'ring!",
        parse_mode="HTML",
        reply_markup=kb.product_list(products, "case"),
    )
    await call.answer()


@router.callback_query(F.data == "shop:unban")
async def cb_shop_unban(call: CallbackQuery) -> None:
    products = await repo.get_products(category="unban")
    await call.message.edit_text(
        "✔️ <b>Unban</b>\n\n"
        "Agar hisobingiz bloklangan bo'lsa, unban xarid qilib\n"
        "serverga qaytishingiz mumkin.",
        parse_mode="HTML",
        reply_markup=kb.product_list(products, "unban"),
    )
    await call.answer()


@router.callback_query(F.data.startswith("product:"))
async def cb_product_detail(call: CallbackQuery) -> None:
    product_id = int(call.data.split(":")[1])
    product = await repo.get_product(product_id)
    if not product:
        await call.answer("Mahsulot topilmadi.", show_alert=True)
        return

    await call.message.edit_text(
        product_card(product),
        parse_mode="HTML",
        reply_markup=kb.product_detail(product_id),
    )
    await call.answer()


@router.callback_query(F.data.startswith("buy:"))
async def cb_buy(call: CallbackQuery, db_user: dict) -> None:
    product_id = int(call.data.split(":")[1])

    # Must have a Minecraft nickname
    if not db_user.get("mc_nickname"):
        await call.answer(
            "⚠️ Avval Minecraft Nicknameingizni bog'lashingiz kerak!\n"
            "Profil → Nickname bog'lash bo'limiga o'ting.",
            show_alert=True,
        )
        return

    product = await repo.get_product(product_id)
    if not product:
        await call.answer("Mahsulot topilmadi.", show_alert=True)
        return

    # Check for duplicate pending order
    has_pending = await repo.has_pending_order(call.from_user.id, product_id)
    if has_pending:
        await call.answer(
            "⚠️ Ushbu mahsulot uchun sizda kutilayotgan buyurtma mavjud!\n"
            "Admin tasdiqlashini kuting yoki buyurtmani bekor qiling.",
            show_alert=True,
        )
        return

    from utils.helpers import fmt_price
    await call.message.edit_text(
        f"💳 <b>To'lov usulini tanlang</b>\n\n"
        f"{product['emoji']} <b>{product['name']}</b>\n"
        f"💵 Narxi: <b>{fmt_price(product['price'])}</b>\n\n"
        f"🎮 Yetkazib berish: <b>{db_user['mc_nickname']}</b>\n\n"
        f"Qanday usulda to'lashni xohlaysiz:",
        parse_mode="HTML",
        reply_markup=kb.payment_method(product_id),
    )
    await call.answer()

@router.callback_query(F.data.startswith("apply_promo:"))
async def cb_promo_prompt(call: CallbackQuery, state: FSMContext) -> None:
    product_id = int(call.data.split(":")[1])
    await state.set_state(PromoState.waiting_for_promo)
    await state.update_data(product_id=product_id)
    await call.message.edit_text(
        "🎁 <b>Promo-kodni kiriting:</b>\n\nMasalan: <code>START2024</code>",
        parse_mode="HTML",
        reply_markup=kb.back_button(f"buy:{product_id}")
    )
    await call.answer()

@router.message(PromoState.waiting_for_promo)
async def process_promo_code(message: Message, state: FSMContext, bot: Any) -> None:
    code = message.text.strip().upper()
    data = await state.get_data()
    product_id = data['product_id']
    
    promo = await repo.get_promo_by_code(code) # Assuming this method exists
    if not promo:
        await message.answer("❌ Bunday promo-kod topilmadi yoki muddati o'tgan.")
        return

    product = await repo.get_product(product_id)
    discount_percent = promo['discount']
    new_price = product['price'] * (1 - discount_percent / 100)
    
    await state.clear()
    await message.answer(f"🎉 Tabriklaymiz! <b>{discount_percent}%</b> chegirma yutdingiz!", parse_mode="HTML")

    if new_price <= 0:
        # 0% ga teng bo'lsa to'lovni olib tashlaymiz
        await message.answer("🎁 Ushbu mahsulot siz uchun mutlaqo <b>BEPUL</b>!", parse_mode="HTML")
        
        db_user = await repo.get_user(message.from_user.id)
        order_id = await repo.create_order(
            telegram_id=message.from_user.id,
            product_id=product_id,
            mc_nickname=db_user["mc_nickname"],
            amount=0,
            payment_method="promo",
        )
        
        # Darhol yetkazib berish
        ok, result = await deliver_order(order_id, admin_id=0) # System delivery
        if ok:
            await message.answer(
                f"✅ Buyurtma muvaffaqiyatli bajarildi!\nMahsulot <b>{db_user['mc_nickname']}</b> hisobiga yetkazildi.",
                reply_markup=kb.main_menu()
            )
        else:
            await message.answer(f"⚠️ Xatolik yuz berdi: {result}\nIltimos admin bilan bog'laning.")
    else:
        from utils.helpers import fmt_price
        await message.answer(
            f"💰 <b>Chegirmali narx:</b> <s>{fmt_price(product['price'])}</s> → <b>{fmt_price(new_price)}</b>\n\n"
            f"To'lov usulini tanlang:",
            parse_mode="HTML",
            reply_markup=kb.payment_method(product_id, price=new_price)
        )
