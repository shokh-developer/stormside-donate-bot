"""
keyboards/keyboards.py – all inline keyboard builders.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ──────────────────────────────────────────────────────────────────────────────
# Main Menu
# ──────────────────────────────────────────────────────────────────────────────

def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="🛒 Do'kon", callback_data="shop:main"),
        InlineKeyboardButton(text="👤 Profil", callback_data="profile"),
    )
    kb.row(
        InlineKeyboardButton(text="📋 Buyurtmalar", callback_data="my_orders"),
        InlineKeyboardButton(text="ℹ️ Ma'lumotlar", callback_data="help"),
    )
    kb.row(
        InlineKeyboardButton(text="🏆 Top O'yinchilar", callback_data="top_donators"),
        InlineKeyboardButton(text="✍️ Bog'lanish", callback_data="support_ticket"),
    )
    return kb.as_markup()


def back_home() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="home"),
    )
    return kb.as_markup()


def back_button(callback: str, label: str = "⬅️ Orqaga") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=label, callback_data=callback))
    return kb.as_markup()


# ──────────────────────────────────────────────────────────────────────────────
# Shop
# ──────────────────────────────────────────────────────────────────────────────

def shop_categories() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="⚔️ Ranklar", callback_data="shop:ranks"),
        InlineKeyboardButton(text="🤑 SIDE (Vales)", callback_data="shop:coins"),
    )
    kb.row(
        InlineKeyboardButton(text="🎁 Case'lar", callback_data="shop:cases"),
        InlineKeyboardButton(text="✔️ Unban", callback_data="shop:unban"),
    )
    kb.row(InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="home"))
    return kb.as_markup()


def rank_list(ranks: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for r in ranks:
        kb.row(
            InlineKeyboardButton(
                text=f"{r['emoji']} {r['name']}",
                callback_data=f"rank:{r['lp_group']}",
            )
        )
    kb.row(
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data="shop:main"),
        InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="home"),
    )
    return kb.as_markup()


def rank_duration(monthly: Dict[str, Any], permanent: Dict[str, Any]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(
            text=f"⏳ 1 Oy — {int(monthly['price']):,} UZS",
            callback_data=f"product:{monthly['id']}",
        )
    )
    kb.row(
        InlineKeyboardButton(
            text=f"♾️ Butunlay — {int(permanent['price']):,} UZS",
            callback_data=f"product:{permanent['id']}",
        )
    )
    kb.row(
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data="shop:ranks"),
        InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="home"),
    )
    return kb.as_markup()


def product_list(products: List[Dict[str, Any]], category: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in products:
        price_str = f"{int(p['price']):,} UZS"
        kb.row(
            InlineKeyboardButton(
                text=f"{p['emoji']} {p['name']}  —  {price_str}",
                callback_data=f"product:{p['id']}",
            )
        )
    kb.row(
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data="shop:main"),
        InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="home"),
    )
    return kb.as_markup()


def product_detail(product_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="💳 Sotib olish", callback_data=f"buy:{product_id}"))
    kb.row(
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data="shop:main"),
        InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="home"),
    )
    return kb.as_markup()


# ──────────────────────────────────────────────────────────────────────────────
# Payment
# ──────────────────────────────────────────────────────────────────────────────

def payment_method(product_id: int, price: Optional[float] = None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    price_val = f":{int(price)}" if price is not None else ""
    kb.row(
        InlineKeyboardButton(
            text="💳 Click", callback_data=f"pay:click:{product_id}{price_val}"
        ),
        InlineKeyboardButton(
            text="💳 Payme", callback_data=f"pay:payme:{product_id}{price_val}"
        ),
    )
    kb.row(
        InlineKeyboardButton(
            text="🎁 Promo-kod kiritish", callback_data=f"apply_promo:{product_id}"
        )
    )
    kb.row(
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"product:{product_id}"),
        InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="home"),
    )
    return kb.as_markup()


def after_qr(order_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(
            text="📸 To'lov qildim – Chekni yuborish",
            callback_data=f"await_screenshot:{order_id}",
        )
    )
    kb.row(InlineKeyboardButton(text="❌ Buyurtmani bekor qilish", callback_data=f"cancel_order:{order_id}"))
    kb.row(InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="home"))
    return kb.as_markup()


def cancel_order_confirm(order_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Ha, bekor qilinsin", callback_data=f"do_cancel:{order_id}"),
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"await_screenshot:{order_id}"),
    )
    return kb.as_markup()


# ──────────────────────────────────────────────────────────────────────────────
# Admin Panel
# ──────────────────────────────────────────────────────────────────────────────

def admin_main() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📋 Kutilayotgan buyurtmalar", callback_data="admin:pending"))
    kb.row(
        InlineKeyboardButton(text="📦 Mahsulotlarni boshqarish", callback_data="admin:products")
    )
    kb.row(InlineKeyboardButton(text="🎁 Promo-kodlarni boshqarish", callback_data="admin:promos"))
    kb.row(InlineKeyboardButton(text="👤 Yangi admin qo'shish", callback_data="admin:add_new"))
    kb.row(InlineKeyboardButton(text="📢 Yangilik yuborish", callback_data="admin:news"))
    kb.row(InlineKeyboardButton(text="🔌 RCON test qilish", callback_data="admin:rcon_test"))
    kb.row(InlineKeyboardButton(text="💀 O'yinchini o'ldirish (Kill)", callback_data="admin:kill_player"))
    kb.row(InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="home"))
    return kb.as_markup()


def admin_order_actions(order_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"admin:approve:{order_id}"),
        InlineKeyboardButton(text="❌ Rad etish",  callback_data=f"admin:reject:{order_id}"),
    )
    kb.row(InlineKeyboardButton(text="🗑 Olib qo'yish (Revoke)", callback_data=f"admin:revoke:{order_id}"))
    kb.row(InlineKeyboardButton(text="⬅️ Ro'yxatga qaytish", callback_data="admin:pending"))
    return kb.as_markup()


def admin_pending_list(orders: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for o in orders:
        kb.row(
            InlineKeyboardButton(
                text=f"#{o['id']} {o['emoji']} {o['product_name']} – {o['mc_nickname']}",
                callback_data=f"admin:order:{o['id']}",
            )
        )
    kb.row(InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin:pending"))
    kb.row(InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="home"))
    return kb.as_markup()


def admin_products_list(products: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in products:
        status = "✅" if p['is_active'] else "❌"
        kb.row(
            InlineKeyboardButton(
                text=f"{status} {p['emoji']} {p['name']} — {int(p['price']):,} UZS",
                callback_data=f"admin:edit_prod:{p['id']}",
            )
        )
    kb.row(InlineKeyboardButton(text="➕ Yangi mahsulot qo'shish", callback_data="admin:add_product"))
    kb.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:main_panel"))
    return kb.as_markup()


def admin_category_selector() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="⚔️ Rank", callback_data="admin:set_cat:rank"),
        InlineKeyboardButton(text="🤑 Coins", callback_data="admin:set_cat:coins"),
    )
    kb.row(
        InlineKeyboardButton(text="🎁 Case", callback_data="admin:set_cat:case"),
        InlineKeyboardButton(text="✔️ Unban", callback_data="admin:set_cat:unban"),
    )
    kb.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin:products"))
    return kb.as_markup()


def admin_product_edit(product_id: int, is_active: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(
            text="💰 Narxni o'zgartirish",
            callback_data=f"admin:set_price:{product_id}",
        )
    )
    status_text = "🔴 O'chirish (Deactivate)" if is_active else "🟢 Yoqish (Activate)"
    kb.row(
        InlineKeyboardButton(
            text=status_text,
            callback_data=f"admin:toggle_prod:{product_id}:{int(not is_active)}",
        )
    )
    kb.row(
        InlineKeyboardButton(text="⬅️ Ro'yxatga qaytish", callback_data="admin:products"),
        InlineKeyboardButton(text="🏠 Admin Panel", callback_data="admin:main_panel"),
    )
    return kb.as_markup()


def admin_reject_reason(order_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(
            text="💰 Takroriy to'lov",
            callback_data=f"admin:reject_reason:{order_id}:duplicate",
        )
    )
    kb.row(
        InlineKeyboardButton(
            text="🖼 Noto'g'ri chek",
            callback_data=f"admin:reject_reason:{order_id}:invalid_screenshot",
        )
    )
    kb.row(
        InlineKeyboardButton(
            text="❓ Boshqa sabab",
            callback_data=f"admin:reject_reason:{order_id}:other",
        )
    )
    kb.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"admin:order:{order_id}"))
    return kb.as_markup()


# ──────────────────────────────────────────────────────────────────────────────
# Profile / Orders
# ──────────────────────────────────────────────────────────────────────────────

def profile_menu(has_nickname: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if has_nickname:
        kb.row(
            InlineKeyboardButton(text="✏️ Nicknameni o'zgartirish", callback_data="set_nickname")
        )
    else:
        kb.row(
            InlineKeyboardButton(text="🎮 MC Nickname bog'lash", callback_data="set_nickname")
        )
    kb.row(
        InlineKeyboardButton(text="📋 Buyurtmalar tarixi", callback_data="my_orders"),
        InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="home"),
    )
    return kb.as_markup()

def admin_promo_list(promos: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in promos:
        kb.row(InlineKeyboardButton(text=f"🎟 {p['code']} ({p['discount']}% off)", callback_data=f"admin:del_promo:{p['id']}"))
    kb.row(InlineKeyboardButton(text="➕ Yangi promo qo'shish", callback_data="admin:add_promo"))
    kb.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:main_panel"))
    return kb.as_markup()

def support_reply_markup(user_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="💬 Javob berish", callback_data=f"admin:reply_ticket:{user_id}")
    )
    return kb.as_markup()
