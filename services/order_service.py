"""
services/order_service.py – business logic for order approval / rejection.
"""
from __future__ import annotations

import logging
from typing import Tuple

from db import repository as repo
from services.rcon_service import rcon

logger = logging.getLogger(__name__)


async def deliver_order(order_id: int, admin_id: int) -> Tuple[bool, str]:
    """
    Approve an order:
    1. Fetch order details.
    2. Send appropriate RCON command.
    3. Update order status.
    4. Log admin action.
    """
    order = await repo.get_order(order_id)
    if not order:
        return False, "Order not found."

    if order["status"] != "pending":
        return False, f"Order already {order['status']}."

    nickname = order["mc_nickname"]
    category = order["category"]
    cmd_used = ""

    if category == "rank":
        lp_group = order["lp_group"]
        ok, result = await rcon.give_rank(nickname, lp_group)
        cmd_used = f"lp user {nickname} parent add {lp_group}"
    elif category == "coins":
        amount = order["coins_amount"] or 0
        ok, result = await rcon.give_coins(nickname, amount)
        cmd_used = f"eco give {nickname} {amount}"
    else:
        ok, result = False, f"Unknown category: {category}"

    final_status = "delivered" if ok else "approved"  # approved but not delivered if RCON failed

    await repo.update_order_status(
        order_id,
        status=final_status,
        admin_id=admin_id,
        rcon_command=cmd_used,
        rcon_result=result,
    )
    await repo.log_admin_action(
        admin_id=admin_id,
        action=f"approve→{final_status}",
        target_order_id=order_id,
        note=result,
    )

    if ok:
        # Bonus announcement on server
        await rcon.announce(
            f"&6[Stromeside] &e{nickname} &7just got &b{order['product_name']}&7! "
            f"&fDonate at t.me/StromesideBot"
        )
        return True, result
    else:
        return False, result


async def reject_order(order_id: int, admin_id: int, reason: str = "") -> bool:
    order = await repo.get_order(order_id)
    if not order or order["status"] != "pending":
        return False

    await repo.update_order_status(
        order_id,
        status="rejected",
        admin_id=admin_id,
        admin_note=reason or "Rejected by admin.",
    )
    await repo.log_admin_action(
        admin_id=admin_id,
        action="reject",
        target_order_id=order_id,
        note=reason,
    )
    return True
