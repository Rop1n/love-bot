import json
from datetime import datetime
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload

from app.database.models import (
    async_session,
    User,
    Currency,
    UserCurrency,
    Gift,
    GiftPrice,
    GiftOrder,
    GiftContent,
    CurrencyRequest,
    ActionLog,
)


def now_ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_prefix() -> str:
    return datetime.now().strftime("%Y-%m-%d")


async def create_log(user_id: int | None, action: str, details: str):
    async with async_session() as session:
        log = ActionLog(user_id=user_id, action=action, details=details, created_at=now_ts())
        session.add(log)
        await session.commit()


async def ensure_users(admin_id: int, client_id: int):
    async with async_session() as session:
        async with session.begin():
            for tg_id, role in [(admin_id, "admin"), (client_id, "client")]:
                user = await session.scalar(select(User).where(User.tg_id == tg_id))
                if user:
                    user.role = role
                else:
                    session.add(User(tg_id=tg_id, role=role))


async def get_user_role(tg_id: int) -> str | None:
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        return user.role if user else None


async def get_user_by_tg(tg_id: int) -> User | None:
    async with async_session() as session:
        return await session.scalar(select(User).where(User.tg_id == tg_id))


async def get_admins() -> list[User]:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.role == "admin"))
        return result.scalars().all()


async def get_client() -> User | None:
    async with async_session() as session:
        return await session.scalar(select(User).where(User.role == "client"))


async def get_user_balances(tg_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(UserCurrency)
            .join(User)
            .options(selectinload(UserCurrency.currency))
            .where(User.tg_id == tg_id)
            .order_by(UserCurrency.id)
        )
        return result.scalars().all()


async def add_balance(tg_id: int, currency_id: int, amount: int):
    async with async_session() as session:
        async with session.begin():
            user = await session.scalar(select(User).where(User.tg_id == tg_id))
            if not user:
                return False
            row = await session.scalar(
                select(UserCurrency).where(
                    UserCurrency.user_id == user.id,
                    UserCurrency.currency_id == currency_id
                )
            )
            if row:
                row.amount += amount
            else:
                session.add(UserCurrency(user_id=user.id, currency_id=currency_id, amount=amount))
        return True


async def count_awards_today(user_id: int, currency_id: int) -> int:
    prefix = today_prefix()
    async with async_session() as session:
        result = await session.execute(
            select(func.count(ActionLog.id))
            .where(ActionLog.user_id == user_id)
            .where(ActionLog.action == "currency_add")
            .where(ActionLog.details.like(f"%\"currency_id\": {currency_id}%"))
            .where(ActionLog.created_at.like(f"{prefix}%"))
        )
        return int(result.scalar() or 0)


# ------------------ CURRENCY ------------------

async def create_currency(name: str, icon: str, description: str, daily_limit: int | None):
    async with async_session() as session:
        currency = Currency(name=name, icon=icon, description=description, daily_limit=daily_limit)
        session.add(currency)
        await session.commit()
        await session.refresh(currency)
        return currency


async def get_currency(currency_id: int):
    async with async_session() as session:
        return await session.scalar(select(Currency).where(Currency.id == currency_id))


async def get_all_currencies() -> list[Currency]:
    async with async_session() as session:
        result = await session.execute(select(Currency).order_by(Currency.id))
        return result.scalars().all()


async def update_currency_field(currency_id: int, field: str, value):
    async with async_session() as session:
        stmt = update(Currency).where(Currency.id == currency_id).values({field: value})
        await session.execute(stmt)
        await session.commit()


async def delete_currency(currency_id: int):
    async with async_session() as session:
        stmt = delete(Currency).where(Currency.id == currency_id)
        await session.execute(stmt)
        await session.commit()


# ------------------ GIFT ------------------

async def create_gift_with_prices(
    name: str,
    description: str | None,
    max_orders: int | None,
    delivery: str,
    prices: list[dict]
) -> dict:
    delivery = "manual"
    normalized = []
    for p in prices or []:
        cid = int(p.get("currency_id"))
        amt = int(p.get("amount"))
        if amt < 1:
            raise ValueError("amount must be >= 1")
        normalized.append({"currency_id": cid, "amount": amt})

    async with async_session() as session:
        async with session.begin():
            gift = Gift(name=name, description=description, max_orders=max_orders, delivery=delivery)
            session.add(gift)
            await session.flush()
            gift_id = gift.id

            for p in normalized:
                session.add(GiftPrice(gift_id=gift_id, currency_id=p["currency_id"], amount=p["amount"]))

            result = await session.execute(
                select(Gift)
                .options(selectinload(Gift.prices).selectinload(GiftPrice.currency))
                .where(Gift.id == gift_id)
            )
            gift_loaded = result.scalar_one()

            dto = {
                "id": gift_loaded.id,
                "name": gift_loaded.name,
                "description": gift_loaded.description,
                "max_orders": gift_loaded.max_orders,
                "delivery": gift_loaded.delivery,
                "prices": []
            }
            for gp in gift_loaded.prices:
                dto["prices"].append({
                    "id": gp.id,
                    "amount": gp.amount,
                    "currency_id": gp.currency.id,
                    "currency_name": gp.currency.name,
                    "currency_icon": gp.currency.icon,
                })

        return dto


async def get_gift_with_prices(gift_id: int) -> dict | None:
    async with async_session() as session:
        result = await session.execute(
            select(Gift)
            .options(selectinload(Gift.prices).selectinload(GiftPrice.currency))
            .where(Gift.id == gift_id)
        )
        gift = result.scalar_one_or_none()
        if not gift:
            return None

        dto = {
            "id": gift.id,
            "name": gift.name,
            "description": gift.description,
            "max_orders": gift.max_orders,
            "delivery": "manual",
            "prices": []
        }

        for p in gift.prices:
            dto["prices"].append({
                "id": p.id,
                "amount": p.amount,
                "currency_id": p.currency.id,
                "currency_name": p.currency.name,
                "currency_icon": p.currency.icon,
            })

        return dto


async def get_gift_with_price_by_price_id(price_id: int) -> dict | None:
    async with async_session() as session:
        result = await session.execute(
            select(GiftPrice)
            .options(
                selectinload(GiftPrice.gift).selectinload(Gift.prices).selectinload(GiftPrice.currency),
                selectinload(GiftPrice.currency)
            )
            .where(GiftPrice.id == price_id)
        )
        price = result.scalar_one_or_none()
        if not price:
            return None

        gift = price.gift
        dto = {
            "id": gift.id,
            "name": gift.name,
            "description": gift.description,
            "max_orders": gift.max_orders,
            "delivery": "manual",
            "prices": []
        }

        for p in gift.prices:
            dto["prices"].append({
                "id": p.id,
                "amount": p.amount,
                "currency_id": p.currency.id,
                "currency_name": p.currency.name,
                "currency_icon": p.currency.icon,
            })

        return dto


async def get_all_gifts():
    async with async_session() as session:
        result = await session.execute(select(Gift))
        return result.scalars().all()


async def update_gift_name(gift_id: int, new_name: str):
    async with async_session() as session:
        gift = await session.get(Gift, gift_id)
        if not gift:
            return
        gift.name = new_name
        await session.commit()


async def update_gift_description(gift_id: int, new_description: str):
    async with async_session() as session:
        gift = await session.get(Gift, gift_id)
        if not gift:
            return
        gift.description = new_description
        await session.commit()


async def update_gift_limit(gift_id: int, limit: int | None):
    async with async_session() as session:
        gift = await session.get(Gift, gift_id)
        if not gift:
            return
        gift.max_orders = limit
        await session.commit()


async def update_gift_delivery(gift_id: int, delivery: str):
    async with async_session() as session:
        gift = await session.get(Gift, gift_id)
        if not gift:
            return
        gift.delivery = "manual"
        await session.commit()


async def update_gift_price(price_id: int, amount: int):
    async with async_session() as session:
        result = await session.execute(select(GiftPrice).where(GiftPrice.id == price_id))
        price = result.scalar_one_or_none()
        if not price:
            return
        price.amount = amount
        session.add(price)
        await session.commit()


async def delete_gift(gift_id: int):
    async with async_session() as session:
        gift = await session.get(Gift, gift_id)
        if not gift:
            return
        await session.delete(gift)
        await session.commit()


async def add_gift_price(gift_id: int, currency_id: int, amount: int):
    async with async_session() as session:
        price = await session.execute(
            select(GiftPrice).where(GiftPrice.gift_id == gift_id, GiftPrice.currency_id == currency_id)
        )
        existing = price.scalar_one_or_none()
        if existing:
            existing.amount = amount
        else:
            session.add(GiftPrice(gift_id=gift_id, currency_id=currency_id, amount=amount))
        await session.commit()


async def delete_gift_price(price_id: int):
    async with async_session() as session:
        await session.execute(delete(GiftPrice).where(GiftPrice.id == price_id))
        await session.commit()


async def get_gift_content(gift_id: int) -> GiftContent | None:
    async with async_session() as session:
        result = await session.execute(select(GiftContent).where(GiftContent.gift_id == gift_id))
        return result.scalar_one_or_none()


async def set_gift_content(gift_id: int, kind: str, data: str, caption: str | None):
    async with async_session() as session:
        async with session.begin():
            existing = await session.scalar(select(GiftContent).where(GiftContent.gift_id == gift_id))
            if existing:
                existing.kind = kind
                existing.data = data
                existing.caption = caption
            else:
                session.add(GiftContent(gift_id=gift_id, kind=kind, data=data, caption=caption))


async def clear_gift_content(gift_id: int):
    async with async_session() as session:
        await session.execute(delete(GiftContent).where(GiftContent.gift_id == gift_id))
        await session.commit()


# ------------------ CURRENCY REQUESTS ------------------

async def create_currency_request(tg_id: int, currency_id: int, comment: str):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if not user:
            return None
        request = CurrencyRequest(
            user_id=user.id,
            currency_id=currency_id,
            comment=comment,
            status="pending",
            created_at=now_ts()
        )
        session.add(request)
        await session.commit()
        await session.refresh(request)
        return request


async def get_pending_currency_requests():
    async with async_session() as session:
        result = await session.execute(
            select(CurrencyRequest)
            .options(selectinload(CurrencyRequest.user), selectinload(CurrencyRequest.currency))
            .where(CurrencyRequest.status == "pending")
            .order_by(CurrencyRequest.id)
        )
        return result.scalars().all()


async def get_pending_requests_count():
    async with async_session() as session:
        result = await session.execute(
            select(func.count(CurrencyRequest.id)).where(CurrencyRequest.status == "pending")
        )
        return int(result.scalar() or 0)


async def get_currency_requests_for_user(tg_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(CurrencyRequest)
            .join(User)
            .options(selectinload(CurrencyRequest.currency))
            .where(User.tg_id == tg_id)
            .order_by(CurrencyRequest.id.desc())
        )
        return result.scalars().all()


async def get_currency_request_by_id(request_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(CurrencyRequest)
            .options(selectinload(CurrencyRequest.user), selectinload(CurrencyRequest.currency))
            .where(CurrencyRequest.id == request_id)
        )
        req = result.scalar_one_or_none()
        if not req:
            return None
        return {
            "id": req.id,
            "user_tg_id": req.user.tg_id,
            "currency_name": req.currency.name,
            "currency_icon": req.currency.icon,
            "comment": req.comment,
            "created_at": req.created_at,
        }


async def approve_currency_request(request_id: int, admin_tg_id: int):
    async with async_session() as session:
        async with session.begin():
            request = await session.get(CurrencyRequest, request_id)
            if not request or request.status != "pending":
                return None

            user = await session.get(User, request.user_id)
            if not user:
                return None

            currency = await session.get(Currency, request.currency_id)
            if not currency:
                return None

            if currency.daily_limit is not None:
                count_today = await count_awards_today(user.id, currency.id)
                if count_today >= currency.daily_limit:
                    return "limit"

            request.status = "approved"
            request.decided_at = now_ts()
            request.decided_by = admin_tg_id

            row = await session.scalar(
                select(UserCurrency).where(
                    UserCurrency.user_id == request.user_id,
                    UserCurrency.currency_id == request.currency_id
                )
            )
            if row:
                row.amount += 1
            else:
                session.add(UserCurrency(user_id=request.user_id, currency_id=request.currency_id, amount=1))

            user_id = user.id
            currency_id = currency.id

        await create_log(user_id, "currency_add", json.dumps({"currency_id": currency_id, "amount": 1}))
        return request


async def reject_currency_request(request_id: int, admin_tg_id: int):
    async with async_session() as session:
        request = await session.get(CurrencyRequest, request_id)
        if not request or request.status != "pending":
            return None
        request.status = "rejected"
        request.decided_at = now_ts()
        request.decided_by = admin_tg_id
        await session.commit()
        return request


# ------------------ ORDERS ------------------

async def count_user_gift_orders(user_id: int, gift_id: int) -> int:
    async with async_session() as session:
        result = await session.execute(
            select(func.count(GiftOrder.id))
            .where(GiftOrder.user_id == user_id, GiftOrder.gift_id == gift_id)
            .where(GiftOrder.status != "rejected")
        )
        return int(result.scalar() or 0)


async def create_gift_order(user_id: int, gift_id: int, status: str, price_snapshot: str):
    async with async_session() as session:
        order = GiftOrder(
            user_id=user_id,
            gift_id=gift_id,
            status=status,
            created_at=now_ts(),
            updated_at=None,
            price_snapshot=price_snapshot
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)
        return order


async def get_order(order_id: int) -> GiftOrder | None:
    async with async_session() as session:
        return await session.scalar(select(GiftOrder).where(GiftOrder.id == order_id))


async def get_order_with_user(order_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(GiftOrder)
            .options(selectinload(GiftOrder.user), selectinload(GiftOrder.gift))
            .where(GiftOrder.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            return None
        return {
            "id": order.id,
            "user_tg_id": order.user.tg_id,
            "gift_name": order.gift.name,
            "status": order.status,
            "price_snapshot": order.price_snapshot,
        }


async def get_orders_for_user(tg_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(GiftOrder)
            .join(User)
            .options(selectinload(GiftOrder.gift))
            .where(User.tg_id == tg_id)
            .order_by(GiftOrder.id.desc())
        )
        return result.scalars().all()


async def get_pending_orders():
    async with async_session() as session:
        result = await session.execute(
            select(GiftOrder)
            .options(selectinload(GiftOrder.gift), selectinload(GiftOrder.user))
            .where(GiftOrder.status == "pending")
            .order_by(GiftOrder.id)
        )
        return result.scalars().all()


async def mark_order_status(order_id: int, status: str, note: str | None = None):
    async with async_session() as session:
        order = await session.get(GiftOrder, order_id)
        if not order:
            return None
        order.status = status
        order.note = note
        order.updated_at = now_ts()
        await session.commit()
        return order


async def refund_order(order_id: int):
    async with async_session() as session:
        async with session.begin():
            order = await session.get(GiftOrder, order_id)
            if not order or not order.price_snapshot:
                return False
            data = json.loads(order.price_snapshot)
            for item in data:
                row = await session.scalar(
                    select(UserCurrency).where(
                        UserCurrency.user_id == order.user_id,
                        UserCurrency.currency_id == item["currency_id"]
                    )
                )
                if row:
                    row.amount += int(item["amount"])
                else:
                    session.add(UserCurrency(user_id=order.user_id, currency_id=item["currency_id"], amount=int(item["amount"])))
        return True


async def purchase_gift(tg_id: int, gift_id: int):
    async with async_session() as session:
        async with session.begin():
            user = await session.scalar(select(User).where(User.tg_id == tg_id))
            if not user:
                return {"ok": False, "error": "user_not_found"}

            gift_result = await session.execute(
                select(Gift)
                .options(selectinload(Gift.prices).selectinload(GiftPrice.currency))
                .where(Gift.id == gift_id)
            )
            gift = gift_result.scalar_one_or_none()
            if not gift:
                return {"ok": False, "error": "gift_not_found"}

            if gift.max_orders is not None:
                count = await session.execute(
                    select(func.count(GiftOrder.id))
                    .where(GiftOrder.user_id == user.id, GiftOrder.gift_id == gift.id)
                    .where(GiftOrder.status != "rejected")
                )
                if int(count.scalar() or 0) >= gift.max_orders:
                    return {"ok": False, "error": "gift_limit"}

            price_snapshot = []
            for price in gift.prices:
                price_snapshot.append({
                    "currency_id": price.currency.id,
                    "currency_name": price.currency.name,
                    "currency_icon": price.currency.icon,
                    "amount": price.amount
                })

            for price in gift.prices:
                row = await session.scalar(
                    select(UserCurrency).where(
                        UserCurrency.user_id == user.id,
                        UserCurrency.currency_id == price.currency.id
                    )
                )
                if not row or row.amount < price.amount:
                    return {"ok": False, "error": "no_balance", "need": price_snapshot}

            for price in gift.prices:
                row = await session.scalar(
                    select(UserCurrency).where(
                        UserCurrency.user_id == user.id,
                        UserCurrency.currency_id == price.currency.id
                    )
                )
                row.amount -= price.amount

            status = "pending"
            order = GiftOrder(
                user_id=user.id,
                gift_id=gift.id,
                status=status,
                created_at=now_ts(),
                updated_at=None,
                price_snapshot=json.dumps(price_snapshot, ensure_ascii=False)
            )
            session.add(order)

            await session.flush()

            user_id = user.id
            gift_info = {"id": gift.id, "name": gift.name, "delivery": "manual"}
            order_info = {"id": order.id, "status": order.status}

        await create_log(user_id, "gift_purchase", json.dumps({"gift_id": gift_info["id"], "status": order_info["status"]}))
        return {"ok": True, "gift": gift_info, "order": order_info, "price": price_snapshot}
