import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

import app.keyboards as kb
import app.database.requests as rq
from app.utils.formatting import (
    format_balance,
    format_gift_card,
    format_order_admin,
    format_order_client,
    format_request_client,
)

router = Router()


class ClientCurrencyRequestFSM(StatesGroup):
    waiting_comment = State()


@router.callback_query(F.data == "client:balance")
async def client_balance(callback: CallbackQuery, role: str):
    if role != "client":
        await callback.answer("Нет доступа", show_alert=True)
        return
    balances = await rq.get_user_balances(callback.from_user.id)
    if not balances:
        await callback.message.answer("Баланс пуст", reply_markup=kb.back_to_menu_kb("client"))
        await callback.answer()
        return
    text = format_balance(balances)
    await callback.message.answer(text, reply_markup=kb.back_to_menu_kb("client"), parse_mode="MarkdownV2")
    await callback.answer()


@router.callback_query(F.data == "client:request_currency")
async def client_request_currency(callback: CallbackQuery, role: str):
    if role != "client":
        await callback.answer("Нет доступа", show_alert=True)
        return
    currencies = await rq.get_all_currencies()
    if not currencies:
        await callback.message.answer("Нет доступных валют", reply_markup=kb.back_to_menu_kb("client"))
        await callback.answer()
        return
    await callback.message.answer(
        "Выберите валюту:",
        reply_markup=kb.currencies_kb(currencies, "client:req_currency")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("client:req_currency:"))
async def client_request_currency_choose(callback: CallbackQuery, state: FSMContext, role: str):
    if role != "client":
        await callback.answer("Нет доступа", show_alert=True)
        return
    currency_id = int(callback.data.split(":")[2])
    currency = await rq.get_currency(currency_id)
    user = await rq.get_user_by_tg(callback.from_user.id)
    if not currency or not user:
        await callback.answer("Ошибка данных", show_alert=True)
        return
    if currency.daily_limit is not None:
        count_today = await rq.count_awards_today(user.id, currency.id)
        if count_today >= currency.daily_limit:
            await callback.message.answer("Дневной лимит уже достигнут")
            await callback.answer()
            return
    await state.update_data(currency_id=currency_id, currency_name=currency.name, currency_icon=currency.icon)
    await state.set_state(ClientCurrencyRequestFSM.waiting_comment)
    await callback.message.answer(
        f"Вы выбрали: {currency.icon} {currency.name}\nНапишите комментарий:",
        reply_markup=kb.cancel_kb()
    )
    await callback.answer()


@router.message(ClientCurrencyRequestFSM.waiting_comment)
async def client_request_currency_comment(message: Message, state: FSMContext):
    comment = message.text.strip()
    if not comment:
        await message.answer("Комментарий не может быть пустым")
        return
    data = await state.get_data()
    currency_id = data.get("currency_id")
    req = await rq.create_currency_request(message.from_user.id, currency_id, comment)
    if not req:
        await message.answer("Не удалось создать заявку")
        await state.clear()
        return
    await rq.create_log(None, "currency_request", json.dumps({"request_id": req.id}))
    await message.answer("Заявка отправлена", reply_markup=kb.back_to_menu_kb("client"))
    admins = await rq.get_admins()
    for admin in admins:
        try:
            await message.bot.send_message(admin.tg_id, f"Новая заявка на валюту #{req.id}")
        except Exception:
            pass
    await state.clear()


@router.callback_query(F.data == "client:requests")
async def client_requests(callback: CallbackQuery, role: str):
    if role != "client":
        await callback.answer("Нет доступа", show_alert=True)
        return
    requests = await rq.get_currency_requests_for_user(callback.from_user.id)
    if not requests:
        await callback.message.answer("Заявок пока нет", reply_markup=kb.back_to_menu_kb("client"))
        await callback.answer()
        return
    for req in requests[:10]:
        text = format_request_client(
            req.id,
            req.currency.icon,
            req.currency.name,
            req.comment,
            req.status,
            req.created_at,
        )
        await callback.message.answer(text, parse_mode="MarkdownV2")
    await callback.message.answer("⬅️ В меню", reply_markup=kb.back_to_menu_kb("client"))
    await callback.answer()


@router.callback_query(F.data == "client:gifts")
async def client_gifts(callback: CallbackQuery, role: str):
    if role != "client":
        await callback.answer("Нет доступа", show_alert=True)
        return
    gifts = await rq.get_all_gifts()
    if not gifts:
        await callback.message.answer("Подарков пока нет", reply_markup=kb.back_to_menu_kb("client"))
        await callback.answer()
        return
    for gift in gifts:
        details = await rq.get_gift_with_prices(gift.id)
        text = format_gift_card(details)
        await callback.message.answer(
            text,
            reply_markup=kb.client_gift_kb(details["id"]),
            parse_mode="MarkdownV2",
        )
    await callback.answer()


@router.callback_query(F.data.startswith("client:buy:"))
async def client_buy_gift(callback: CallbackQuery, role: str):
    if role != "client":
        await callback.answer("Нет доступа", show_alert=True)
        return
    gift_id = int(callback.data.split(":")[2])
    result = await rq.purchase_gift(callback.from_user.id, gift_id)
    if not result.get("ok"):
        error = result.get("error")
        if error == "gift_limit":
            await callback.message.answer("Достигнут лимит на этот подарок")
        elif error == "no_balance":
            need = result.get("need", [])
            lines = ["Не хватает валюты:"]
            for p in need:
                lines.append(f"• {p['amount']} {p['currency_icon']} {p['currency_name']}")
            await callback.message.answer("\n".join(lines))
        else:
            await callback.message.answer("Не удалось оформить покупку")
        await callback.answer()
        return

    gift = result["gift"]
    order = result["order"]
    price = result["price"]

    await callback.message.answer(
        f"✅ Заказ оформлен: \\#{order['id']}",
        parse_mode="MarkdownV2",
    )

    admins = await rq.get_admins()
    admin_text = format_order_admin(
        order["id"],
        gift["name"],
        callback.from_user.id,
        order["status"],
        price,
        False,
    )

    for admin in admins:
        try:
            await callback.bot.send_message(
                admin.tg_id,
                admin_text,
                reply_markup=kb.admin_order_kb(order["id"]),
                parse_mode="MarkdownV2",
            )
        except Exception:
            pass
    await callback.bot.send_message(
        callback.from_user.id,
        "⏳ Ожидайте подтверждения администратора",
    )

    await callback.answer()


@router.callback_query(F.data == "client:orders")
async def client_orders(callback: CallbackQuery, role: str):
    if role != "client":
        await callback.answer("Нет доступа", show_alert=True)
        return
    orders = await rq.get_orders_for_user(callback.from_user.id)
    if not orders:
        await callback.message.answer("Заказов пока нет", reply_markup=kb.back_to_menu_kb("client"))
        await callback.answer()
        return
    for order in orders[:10]:
        text = format_order_client(order.id, order.gift.name, order.status, order.created_at)
        await callback.message.answer(text, parse_mode="MarkdownV2")
    await callback.message.answer("⬅️ В меню", reply_markup=kb.back_to_menu_kb("client"))
    await callback.answer()
