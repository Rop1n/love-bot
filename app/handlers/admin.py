import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

import app.keyboards as kb
import app.database.requests as rq
from app.utils.formatting import md_escape, status_label, format_price_lines

from config import CLIENT_ID

router = Router()


class CurrencyCreateFSM(StatesGroup):
    name = State()
    icon = State()
    description = State()
    daily_limit = State()


class CurrencyEditFSM(StatesGroup):
    waiting_value = State()


class GiftCreateFSM(StatesGroup):
    name = State()
    description = State()
    max_orders = State()
    delivery = State()
    waiting_currency_choice = State()
    waiting_amount = State()
    confirm = State()


class GiftEditFSM(StatesGroup):
    new_name = State()
    new_description = State()
    new_limit = State()


class GiftPriceFSM(StatesGroup):
    waiting_currency = State()
    waiting_amount = State()


class GiftPriceEditFSM(StatesGroup):
    waiting_amount = State()


class GiftContentFSM(StatesGroup):
    waiting_content = State()


class AdminGrantFSM(StatesGroup):
    waiting_amount = State()


class ImportGiftsFSM(StatesGroup):
    waiting_file = State()


class AdminMessageFSM(StatesGroup):
    waiting_message = State()


class OrderSendFSM(StatesGroup):
    waiting_content = State()


@router.callback_query(F.data == "admin:currencies")
async def admin_currencies(callback: CallbackQuery, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.answer("Меню валют", reply_markup=kb.admin_currency_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "currency:new")
async def currency_new(callback: CallbackQuery, state: FSMContext, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(CurrencyCreateFSM.name)
    await callback.message.answer("Введите название валюты:", reply_markup=kb.cancel_kb())
    await callback.answer()


@router.message(CurrencyCreateFSM.name)
async def currency_new_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("Название не может быть пустым")
        return
    await state.update_data(name=name)
    await state.set_state(CurrencyCreateFSM.icon)
    await message.answer("Введите иконку (emoji):", reply_markup=kb.cancel_kb())


@router.message(CurrencyCreateFSM.icon)
async def currency_new_icon(message: Message, state: FSMContext):
    icon = message.text.strip()
    if not icon:
        await message.answer("Иконка не может быть пустой")
        return
    await state.update_data(icon=icon)
    await state.set_state(CurrencyCreateFSM.description)
    await message.answer("Введите описание условий получения:", reply_markup=kb.cancel_kb())


@router.message(CurrencyCreateFSM.description)
async def currency_new_description(message: Message, state: FSMContext):
    desc = message.text.strip()
    await state.update_data(description=desc)
    await state.set_state(CurrencyCreateFSM.daily_limit)
    await message.answer("Лимит начислений в день (0 = без лимита):", reply_markup=kb.cancel_kb())


@router.message(CurrencyCreateFSM.daily_limit)
async def currency_new_limit(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("Введите целое число 0 или больше")
        return
    limit = int(text)
    data = await state.get_data()
    await rq.create_currency(
        name=data["name"],
        icon=data["icon"],
        description=data["description"],
        daily_limit=None if limit == 0 else limit,
    )
    await state.clear()
    await message.answer("Валюта создана", reply_markup=kb.admin_currency_menu_kb())


@router.callback_query(F.data == "currency:list")
async def currency_list(callback: CallbackQuery, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    currencies = await rq.get_all_currencies()
    if not currencies:
        await callback.message.answer("Валют пока нет", reply_markup=kb.admin_currency_menu_kb())
        await callback.answer()
        return
    for currency in currencies:
        limit_text = "без лимита" if currency.daily_limit is None else str(currency.daily_limit)
        text = f"{currency.icon} {currency.name}\n{currency.description}\nЛимит в день: {limit_text}"
        await callback.message.answer(text, reply_markup=kb.currency_open_edit_kb(currency.id))
    await callback.answer()


@router.callback_query(F.data.startswith("currency:open:"))
async def currency_open(callback: CallbackQuery, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    currency_id = int(callback.data.split(":")[2])
    currency = await rq.get_currency(currency_id)
    if not currency:
        await callback.message.answer("Валюта не найдена")
        await callback.answer()
        return
    limit_text = "без лимита" if currency.daily_limit is None else str(currency.daily_limit)
    text = f"{currency.icon} {currency.name}\n{currency.description}\nЛимит в день: {limit_text}"
    await callback.message.answer(text, reply_markup=kb.currency_edit_kb(currency_id))
    await callback.answer()


@router.callback_query(F.data.startswith("currency:edit:"))
async def currency_edit(callback: CallbackQuery, state: FSMContext, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    _, _, currency_id, field = callback.data.split(":")
    await state.update_data(currency_id=int(currency_id), field=field)
    await state.set_state(CurrencyEditFSM.waiting_value)
    if field == "daily_limit":
        await callback.message.answer("Введите лимит в день (0 = без лимита):", reply_markup=kb.cancel_kb())
    else:
        await callback.message.answer("Введите новое значение:", reply_markup=kb.cancel_kb())
    await callback.answer()


@router.message(CurrencyEditFSM.waiting_value)
async def currency_edit_value(message: Message, state: FSMContext):
    data = await state.get_data()
    currency_id = data.get("currency_id")
    field = data.get("field")
    value = message.text.strip()
    if field == "daily_limit":
        if not value.isdigit():
            await message.answer("Введите целое число 0 или больше")
            return
        limit = int(value)
        await rq.update_currency_field(currency_id, field, None if limit == 0 else limit)
    else:
        if not value:
            await message.answer("Значение не может быть пустым")
            return
        await rq.update_currency_field(currency_id, field, value)
    await state.clear()
    await message.answer("Валюта обновлена", reply_markup=kb.admin_currency_menu_kb())


@router.callback_query(F.data.startswith("currency:delete:"))
async def currency_delete(callback: CallbackQuery, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    currency_id = int(callback.data.split(":")[2])
    await rq.delete_currency(currency_id)
    await callback.message.answer("Валюта удалена", reply_markup=kb.admin_currency_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "admin:client_balance")
async def admin_client_balance(callback: CallbackQuery, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    balances = await rq.get_user_balances(CLIENT_ID)
    if not balances:
        await callback.message.answer("Баланс пуст", reply_markup=kb.back_to_menu_kb("admin"))
        await callback.answer()
        return
    lines = ["Баланс клиента:"]
    for row in balances:
        lines.append(f"{row.currency.icon} {row.currency.name}: {row.amount}")
    await callback.message.answer("\n".join(lines), reply_markup=kb.back_to_menu_kb("admin"))
    await callback.answer()


@router.callback_query(F.data == "admin:grant_currency")
async def admin_grant_currency(callback: CallbackQuery, state: FSMContext, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    currencies = await rq.get_all_currencies()
    if not currencies:
        await callback.message.answer("Нет валют для начисления", reply_markup=kb.back_to_menu_kb("admin"))
        await callback.answer()
        return
    await callback.message.answer("Выберите валюту:", reply_markup=kb.currencies_kb(currencies, "grant"))
    await callback.answer()


@router.callback_query(F.data.startswith("grant:"))
async def admin_grant_currency_choose(callback: CallbackQuery, state: FSMContext, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    currency_id = int(callback.data.split(":")[1])
    await state.update_data(currency_id=currency_id)
    await state.set_state(AdminGrantFSM.waiting_amount)
    await callback.message.answer("Введите количество для начисления:", reply_markup=kb.cancel_kb())
    await callback.answer()


@router.message(AdminGrantFSM.waiting_amount)
async def admin_grant_currency_amount(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or int(text) < 1:
        await message.answer("Нужно целое число >= 1")
        return
    amount = int(text)
    data = await state.get_data()
    currency_id = data.get("currency_id")
    currency = await rq.get_currency(currency_id)
    client = await rq.get_client()
    if not client or not currency:
        await state.clear()
        await message.answer("Ошибка данных", reply_markup=kb.back_to_menu_kb("admin"))
        return
    if currency.daily_limit is not None:
        count_today = await rq.count_awards_today(client.id, currency.id)
        if count_today >= currency.daily_limit:
            await message.answer("Достигнут дневной лимит", reply_markup=kb.back_to_menu_kb("admin"))
            await state.clear()
            return
    await rq.add_balance(CLIENT_ID, currency_id, amount)
    await rq.create_log(client.id, "currency_add", json.dumps({"currency_id": currency.id, "amount": amount, "source": "manual"}))
    await message.bot.send_message(
        CLIENT_ID,
        f"Вам начислено {amount} {currency.icon} {currency.name}"
    )
    await state.clear()
    await message.answer("Начисление выполнено", reply_markup=kb.back_to_menu_kb("admin"))


@router.callback_query(F.data == "admin:currency_requests")
async def admin_currency_requests(callback: CallbackQuery, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    pending = await rq.get_pending_currency_requests()
    if not pending:
        await callback.message.answer("Нет новых заявок", reply_markup=kb.back_to_menu_kb("admin"))
        await callback.answer()
        return
    await callback.message.answer(f"Новых заявок: {len(pending)}")
    for req in pending:
        text = (
            f"Заявка #{req.id}\n"
            f"Пользователь: {req.user.tg_id}\n"
            f"Валюта: {req.currency.icon} {req.currency.name}\n"
            f"Комментарий: {req.comment}\n"
            f"Время: {req.created_at}"
        )
        await callback.message.answer(text, reply_markup=kb.admin_request_kb(req.id))
    await callback.answer()


@router.callback_query(F.data.startswith("request:approve:"))
async def approve_request(callback: CallbackQuery, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    request_id = int(callback.data.split(":")[2])
    req_details = await rq.get_currency_request_by_id(request_id)
    result = await rq.approve_currency_request(request_id, callback.from_user.id)
    if result == "limit":
        await callback.answer("Дневной лимит уже достигнут", show_alert=True)
        return
    if not result:
        await callback.answer("Заявка не найдена", show_alert=True)
        return
    await callback.message.edit_text(callback.message.text + "\n\n✅ ОДОБРЕНО")
    if req_details:
        await callback.bot.send_message(
            req_details["user_tg_id"],
            f"Заявка #{request_id} одобрена\n{req_details['currency_icon']} {req_details['currency_name']}\nКомментарий: {req_details['comment']}"
        )
    await callback.answer("Одобрено")


@router.callback_query(F.data.startswith("request:reject:"))
async def reject_request(callback: CallbackQuery, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    request_id = int(callback.data.split(":")[2])
    req_details = await rq.get_currency_request_by_id(request_id)
    result = await rq.reject_currency_request(request_id, callback.from_user.id)
    if not result:
        await callback.answer("Заявка не найдена", show_alert=True)
        return
    await callback.message.edit_text(callback.message.text + "\n\n❌ ОТКЛОНЕНО")
    if req_details:
        await callback.bot.send_message(
            req_details["user_tg_id"],
            f"Заявка #{request_id} отклонена\n{req_details['currency_icon']} {req_details['currency_name']}"
        )
    await callback.answer("Отклонено")


@router.callback_query(F.data == "admin:gifts")
async def admin_gifts(callback: CallbackQuery, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.answer("Меню подарков", reply_markup=kb.admin_gift_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "gift:new")
async def gift_new(callback: CallbackQuery, state: FSMContext, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    currencies = await rq.get_all_currencies()
    if not currencies:
        await callback.message.answer("Сначала создайте валюты", reply_markup=kb.back_to_menu_kb("admin"))
        await callback.answer()
        return
    await state.set_state(GiftCreateFSM.name)
    await callback.message.answer("Введите название подарка:", reply_markup=kb.cancel_kb())
    await callback.answer()


@router.message(GiftCreateFSM.name)
async def gift_new_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("Название не может быть пустым")
        return
    await state.update_data(name=name)
    await state.set_state(GiftCreateFSM.description)
    await message.answer("Введите описание:", reply_markup=kb.cancel_kb())


@router.message(GiftCreateFSM.description)
async def gift_new_description(message: Message, state: FSMContext):
    desc = message.text.strip()
    await state.update_data(description=desc)
    await state.set_state(GiftCreateFSM.max_orders)
    await message.answer("Лимит покупок (0 = без лимита):", reply_markup=kb.cancel_kb())


@router.message(GiftCreateFSM.max_orders)
async def gift_new_limit(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or int(text) < 0:
        await message.answer("Введите целое число >= 0")
        return
    await state.update_data(max_orders=int(text))
    await state.set_state(GiftCreateFSM.delivery)
    await message.answer("Выберите тип выдачи:", reply_markup=kb.gift_create_delivery_kb())


@router.callback_query(F.data.startswith("gift:new_delivery:"), GiftCreateFSM.delivery)
async def gift_new_delivery(callback: CallbackQuery, state: FSMContext):
    await state.update_data(delivery="manual", prices=[], current_currency=None)
    currencies = await rq.get_all_currencies()
    await callback.message.answer("Выберите валюту:", reply_markup=kb.currencies_kb(currencies, "gift:new_currency"))
    await state.set_state(GiftCreateFSM.waiting_currency_choice)
    await callback.answer()


@router.callback_query(F.data.startswith("gift:new_currency:"), GiftCreateFSM.waiting_currency_choice)
async def gift_new_choose_currency(callback: CallbackQuery, state: FSMContext):
    currency_id = int(callback.data.split(":")[2])
    currency = await rq.get_currency(currency_id)
    if not currency:
        await callback.answer("Валюта не найдена", show_alert=True)
        return
    await state.update_data(current_currency={"id": currency.id, "name": currency.name, "icon": currency.icon})
    await state.set_state(GiftCreateFSM.waiting_amount)
    await callback.message.answer(f"Введите количество для {currency.icon} {currency.name}:")
    await callback.answer()


@router.message(GiftCreateFSM.waiting_amount)
async def gift_new_amount(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or int(text) < 1:
        await message.answer("Введите целое число >= 1")
        return
    amount = int(text)
    data = await state.get_data()
    current_currency = data.get("current_currency")
    prices = data.get("prices", [])
    for p in prices:
        if p["currency_id"] == current_currency["id"]:
            p["amount"] += amount
            break
    else:
        prices.append({
            "currency_id": current_currency["id"],
            "currency_name": current_currency["name"],
            "currency_icon": current_currency["icon"],
            "amount": amount
        })
    await state.update_data(prices=prices, current_currency=None)
    summary_lines = [f"• {p['currency_icon']} {p['currency_name']}: {p['amount']}" for p in prices]
    await message.answer("Текущая стоимость:\n" + "\n".join(summary_lines), reply_markup=kb.confirm_prices_kb())
    await state.set_state(GiftCreateFSM.confirm)


@router.callback_query(F.data == "gift:price:add", GiftCreateFSM.confirm)
async def gift_new_add_more(callback: CallbackQuery, state: FSMContext):
    currencies = await rq.get_all_currencies()
    await callback.message.answer("Выберите валюту:", reply_markup=kb.currencies_kb(currencies, "gift:new_currency"))
    await state.set_state(GiftCreateFSM.waiting_currency_choice)
    await callback.answer()


@router.callback_query(F.data == "gift:save", GiftCreateFSM.confirm)
async def gift_new_save(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    prices = data.get("prices", [])
    if not prices:
        await callback.answer("Добавьте хотя бы одну цену", show_alert=True)
        return
    max_orders = data.get("max_orders")
    delivery = data.get("delivery")
    gift = await rq.create_gift_with_prices(
        name=data.get("name"),
        description=data.get("description"),
        max_orders=None if max_orders == 0 else max_orders,
        delivery=delivery,
        prices=prices,
    )
    await state.clear()
    await callback.message.answer(f"Подарок «{gift['name']}» создан", reply_markup=kb.admin_gift_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "gift:list")
async def gift_list(callback: CallbackQuery, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    gifts = await rq.get_all_gifts()
    if not gifts:
        await callback.message.answer("Подарков пока нет", reply_markup=kb.admin_gift_menu_kb())
        await callback.answer()
        return
    for gift in gifts:
        text = f"🎁 {gift.name}\n{gift.description}"
        await callback.message.answer(text, reply_markup=kb.gift_list_item_kb(gift.id))
    await callback.answer()


@router.callback_query(F.data.startswith("gift:open:"))
async def gift_open(callback: CallbackQuery, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    gift_id = int(callback.data.split(":")[2])
    gift = await rq.get_gift_with_prices(gift_id)
    if not gift:
        await callback.message.answer("Подарок не найден")
        await callback.answer()
        return
    limit = gift["max_orders"] if gift["max_orders"] else "без ограничений"
    delivery = "вручную"
    text = (
        f"🎁 {gift['name']}\n"
        f"Описание: {gift['description']}\n"
        f"Лимит: {limit}\n"
        f"Тип выдачи: {delivery}"
    )
    if gift["prices"]:
        prices_lines = [f"• {p['amount']} {p['currency_icon']} {p['currency_name']}" for p in gift["prices"]]
        text += "\nЦена:\n" + "\n".join(prices_lines)
    await callback.message.answer(text, reply_markup=kb.gift_edit_kb(gift_id))
    await callback.answer()


@router.callback_query(F.data.startswith("gift:edit:"))
async def gift_edit(callback: CallbackQuery, state: FSMContext, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    _, _, gift_id, field = callback.data.split(":")
    gift_id = int(gift_id)
    await state.update_data(editing_gift_id=gift_id)
    if field == "name":
        await state.set_state(GiftEditFSM.new_name)
        await callback.message.answer("Введите новое имя:", reply_markup=kb.cancel_kb())
    elif field == "description":
        await state.set_state(GiftEditFSM.new_description)
        await callback.message.answer("Введите новое описание:", reply_markup=kb.cancel_kb())
    elif field == "limit":
        await state.set_state(GiftEditFSM.new_limit)
        await callback.message.answer("Введите лимит (0 = без лимита):", reply_markup=kb.cancel_kb())
    elif field == "delivery":
        await callback.message.answer("Выберите тип выдачи:", reply_markup=kb.gift_delivery_kb(gift_id))
    await callback.answer()


@router.message(GiftEditFSM.new_name)
async def gift_edit_name(message: Message, state: FSMContext):
    new_name = message.text.strip()
    data = await state.get_data()
    gift_id = data.get("editing_gift_id")
    if not new_name:
        await message.answer("Имя не может быть пустым")
        return
    await rq.update_gift_name(gift_id, new_name)
    await state.clear()
    await message.answer("Имя обновлено", reply_markup=kb.admin_gift_menu_kb())


@router.message(GiftEditFSM.new_description)
async def gift_edit_description(message: Message, state: FSMContext):
    new_desc = message.text.strip()
    data = await state.get_data()
    gift_id = data.get("editing_gift_id")
    await rq.update_gift_description(gift_id, new_desc)
    await state.clear()
    await message.answer("Описание обновлено", reply_markup=kb.admin_gift_menu_kb())


@router.message(GiftEditFSM.new_limit)
async def gift_edit_limit(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or int(text) < 0:
        await message.answer("Введите целое число >= 0")
        return
    limit = int(text)
    data = await state.get_data()
    gift_id = data.get("editing_gift_id")
    await rq.update_gift_limit(gift_id, None if limit == 0 else limit)
    await state.clear()
    await message.answer("Лимит обновлён", reply_markup=kb.admin_gift_menu_kb())


@router.callback_query(F.data.startswith("gift:delivery:"))
async def gift_edit_delivery(callback: CallbackQuery, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    _, _, gift_id, delivery = callback.data.split(":")
    if gift_id == "0":
        await callback.answer("Используйте создание подарка", show_alert=True)
        return
    await rq.update_gift_delivery(int(gift_id), delivery)
    await callback.message.answer("Тип выдачи обновлён", reply_markup=kb.admin_gift_menu_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("gift:prices:"))
async def gift_price_list(callback: CallbackQuery, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    gift_id = int(callback.data.split(":")[2])
    gift = await rq.get_gift_with_prices(gift_id)
    if not gift:
        await callback.message.answer("Подарок не найден")
        await callback.answer()
        return
    await callback.message.answer(
        f"Цены для «{gift['name']}»:",
        reply_markup=kb.gift_price_list_kb(gift_id, gift["prices"])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("gift:price:add:"))
async def gift_price_add(callback: CallbackQuery, state: FSMContext, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    gift_id = int(callback.data.split(":")[3])
    currencies = await rq.get_all_currencies()
    await state.update_data(editing_gift_id=gift_id)
    await state.set_state(GiftPriceFSM.waiting_currency)
    await callback.message.answer("Выберите валюту:", reply_markup=kb.gift_price_currency_kb(gift_id, currencies))
    await callback.answer()


@router.callback_query(F.data.startswith("gift:price:currency:"), GiftPriceFSM.waiting_currency)
async def gift_price_currency(callback: CallbackQuery, state: FSMContext):
    _, _, _, gift_id, currency_id = callback.data.split(":")
    currency = await rq.get_currency(int(currency_id))
    if not currency:
        await callback.answer("Валюта не найдена", show_alert=True)
        return
    await state.update_data(currency_id=int(currency_id), editing_gift_id=int(gift_id))
    await state.set_state(GiftPriceFSM.waiting_amount)
    await callback.message.answer(f"Введите количество для {currency.icon} {currency.name}:")
    await callback.answer()


@router.message(GiftPriceFSM.waiting_amount)
async def gift_price_amount(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введите число")
        return
    amount = int(message.text)
    data = await state.get_data()
    gift_id = data.get("editing_gift_id")
    currency_id = data.get("currency_id")
    if not gift_id or not currency_id:
        await state.clear()
        await message.answer("Ошибка состояния")
        return
    await rq.add_gift_price(gift_id, currency_id, amount)
    gift = await rq.get_gift_with_prices(gift_id)
    await state.clear()
    await message.answer("Цена сохранена", reply_markup=kb.gift_price_list_kb(gift_id, gift["prices"]))


@router.callback_query(F.data.startswith("gift:price:edit:"))
async def gift_price_edit(callback: CallbackQuery, state: FSMContext, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    price_id = int(callback.data.split(":")[3])
    await state.update_data(editing_price_id=price_id)
    await state.set_state(GiftPriceEditFSM.waiting_amount)
    await callback.message.answer("Введите новое количество:", reply_markup=kb.cancel_kb())
    await callback.answer()


@router.message(GiftPriceEditFSM.waiting_amount)
async def gift_price_edit_amount(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введите число")
        return
    amount = int(message.text)
    data = await state.get_data()
    price_id = data.get("editing_price_id")
    gift = await rq.get_gift_with_price_by_price_id(price_id)
    if not gift:
        await state.clear()
        await message.answer("Цена не найдена")
        return
    await rq.update_gift_price(price_id, amount)
    updated = await rq.get_gift_with_price_by_price_id(price_id)
    await state.clear()
    if not updated:
        await message.answer("Цена обновлена")
        return
    await message.answer("Цена обновлена", reply_markup=kb.gift_price_list_kb(updated["id"], updated["prices"]))


@router.callback_query(F.data.startswith("gift:price:delete:"))
async def gift_price_delete(callback: CallbackQuery, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    price_id = int(callback.data.split(":")[3])
    gift = await rq.get_gift_with_price_by_price_id(price_id)
    if not gift:
        await callback.message.answer("Цена не найдена")
        await callback.answer()
        return
    await rq.delete_gift_price(price_id)
    updated = await rq.get_gift_with_prices(gift["id"])
    await callback.message.answer("Цена удалена", reply_markup=kb.gift_price_list_kb(gift["id"], updated["prices"]))
    await callback.answer()


@router.callback_query(F.data.regexp(r"^gift:content:\d+$"))
async def gift_content_menu(callback: CallbackQuery, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    gift_id = int(callback.data.split(":")[2])
    content = await rq.get_gift_content(gift_id)
    await callback.message.answer(
        "Контент подарка:",
        reply_markup=kb.gift_content_kb(gift_id, bool(content))
    )
    await callback.answer()


@router.callback_query(F.data.startswith("gift:content:set:"))
async def gift_content_set(callback: CallbackQuery, state: FSMContext, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    gift_id = int(callback.data.split(":")[3])
    await state.update_data(editing_gift_id=gift_id)
    await state.set_state(GiftContentFSM.waiting_content)
    await callback.message.answer("Отправьте текст или медиа для этого подарка:", reply_markup=kb.cancel_kb())
    await callback.answer()


@router.message(GiftContentFSM.waiting_content)
async def gift_content_receive(message: Message, state: FSMContext):
    data = await state.get_data()
    gift_id = data.get("editing_gift_id")
    kind = None
    payload = None
    caption = message.caption

    if message.text:
        kind = "text"
        payload = message.text
    elif message.photo:
        kind = "photo"
        payload = message.photo[-1].file_id
    elif message.video:
        kind = "video"
        payload = message.video.file_id
    elif message.document:
        kind = "document"
        payload = message.document.file_id
    elif message.audio:
        kind = "audio"
        payload = message.audio.file_id
    elif message.voice:
        kind = "voice"
        payload = message.voice.file_id

    if not kind:
        await message.answer("Нужно отправить текст или медиа")
        return

    await rq.set_gift_content(gift_id, kind, payload, caption)
    await state.clear()
    await message.answer("Контент сохранён", reply_markup=kb.admin_gift_menu_kb())


@router.callback_query(F.data.startswith("gift:content:clear:"))
async def gift_content_clear(callback: CallbackQuery, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    gift_id = int(callback.data.split(":")[3])
    await rq.clear_gift_content(gift_id)
    await callback.message.answer("Контент удалён", reply_markup=kb.admin_gift_menu_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("gift:delete:"))
async def gift_delete(callback: CallbackQuery, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    gift_id = int(callback.data.split(":")[2])
    await rq.delete_gift(gift_id)
    await callback.message.answer("Подарок удалён", reply_markup=kb.admin_gift_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "admin:gift_orders")
async def admin_gift_orders(callback: CallbackQuery, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    orders = await rq.get_pending_orders()
    if not orders:
        await callback.message.answer("Нет новых заказов", reply_markup=kb.back_to_menu_kb("admin"))
        await callback.answer()
        return
    for order in orders:
        price = []
        if order.price_snapshot:
            price = json.loads(order.price_snapshot)
        text = "\n".join(
            [
                f"*Заказ* \\#{order.id}",
                f"*Подарок:* {md_escape(order.gift.name)}",
                f"*Клиент:* `{order.user.tg_id}`",
                f"*Статус:* {status_label(order.status)}",
                "*Цена:*",
                format_price_lines(price),
            ]
        )
        await callback.message.answer(
            text,
            reply_markup=kb.admin_order_kb(order.id),
            parse_mode="MarkdownV2",
        )
    await callback.answer()


@router.callback_query(F.data.startswith("order:done:"))
async def order_done(callback: CallbackQuery, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    order_id = int(callback.data.split(":")[2])
    order = await rq.mark_order_status(order_id, "done")
    order_info = await rq.get_order_with_user(order_id)
    if not order or not order_info:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    await rq.create_log(None, "order_done", json.dumps({"order_id": order_id}))
    await callback.bot.send_message(
        order_info["user_tg_id"],
        f"✅ Ваш заказ \\#{order_id} выполнен",
        parse_mode="MarkdownV2",
    )
    await callback.answer("Отмечено")


@router.callback_query(F.data.startswith("order:reject:"))
async def order_reject(callback: CallbackQuery, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    order_id = int(callback.data.split(":")[2])
    order = await rq.mark_order_status(order_id, "rejected")
    order_info = await rq.get_order_with_user(order_id)
    if not order or not order_info:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    await rq.refund_order(order_id)
    await rq.create_log(None, "order_reject", json.dumps({"order_id": order_id}))
    await callback.bot.send_message(
        order_info["user_tg_id"],
        f"❌ Ваш заказ \\#{order_id} отклонён, валюта возвращена",
        parse_mode="MarkdownV2",
    )
    await callback.answer("Отклонено")


@router.callback_query(F.data.startswith("order:send:"))
async def order_send(callback: CallbackQuery, state: FSMContext, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    order_id = int(callback.data.split(":")[2])
    await state.update_data(order_id=order_id)
    await state.set_state(OrderSendFSM.waiting_content)
    await callback.message.answer("Отправьте сообщение или медиа для клиента:", reply_markup=kb.cancel_kb())
    await callback.answer()


@router.message(OrderSendFSM.waiting_content)
async def order_send_content(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("order_id")
    order_info = await rq.get_order_with_user(order_id)
    if not order_info:
        await message.answer("Заказ не найден")
        await state.clear()
        return
    await message.bot.copy_message(chat_id=order_info["user_tg_id"], from_chat_id=message.chat.id, message_id=message.message_id)
    await rq.mark_order_status(order_id, "done")
    await rq.create_log(None, "order_send", json.dumps({"order_id": order_id}))
    await state.clear()
    await message.answer("Отправлено клиенту", reply_markup=kb.back_to_menu_kb("admin"))


@router.callback_query(F.data == "admin:import_gifts")
async def import_gifts(callback: CallbackQuery, state: FSMContext, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(ImportGiftsFSM.waiting_file)
    await callback.message.answer("Отправьте JSON файл с подарками:", reply_markup=kb.cancel_kb())
    await callback.answer()


@router.message(ImportGiftsFSM.waiting_file)
async def import_gifts_file(message: Message, state: FSMContext):
    if not message.document:
        await message.answer("Нужно отправить файл .json")
        return
    if not message.document.file_name.lower().endswith(".json"):
        await message.answer("Поддерживается только JSON")
        return
    file = await message.bot.get_file(message.document.file_id)
    data = await message.bot.download_file(file.file_path)
    payload = data.read().decode("utf-8")
    try:
        items = json.loads(payload)
    except Exception:
        await message.answer("Ошибка чтения JSON")
        return
    if not isinstance(items, list):
        await message.answer("JSON должен быть списком объектов")
        return

    currencies = await rq.get_all_currencies()
    currency_by_name = {c.name.lower(): c for c in currencies}
    created = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        description = str(item.get("description", "")).strip()
        max_orders = item.get("max_orders")
        delivery = item.get("delivery", "manual")
        prices = []
        for p in item.get("prices", []):
            currency_val = p.get("currency")
            amount = int(p.get("amount", 0))
            if amount < 1:
                continue
            currency_obj = None
            if isinstance(currency_val, int):
                currency_obj = await rq.get_currency(currency_val)
            elif isinstance(currency_val, str):
                currency_obj = currency_by_name.get(currency_val.lower())
            if not currency_obj:
                continue
            prices.append({"currency_id": currency_obj.id, "amount": amount})
        if not prices:
            continue
        gift = await rq.create_gift_with_prices(
            name=name,
            description=description,
            max_orders=None if not max_orders or int(max_orders) == 0 else int(max_orders),
            delivery=delivery,
            prices=prices
        )
        content = item.get("content")
        if isinstance(content, dict):
            kind = content.get("kind")
            data_value = content.get("data")
            caption = content.get("caption")
            if kind and data_value:
                await rq.set_gift_content(gift["id"], kind, str(data_value), caption)
        created += 1
    await state.clear()
    await message.answer(f"Импорт завершён. Создано: {created}", reply_markup=kb.admin_gift_menu_kb())


@router.callback_query(F.data == "admin:message_client")
async def admin_message_client(callback: CallbackQuery, state: FSMContext, role: str):
    if role != "admin":
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminMessageFSM.waiting_message)
    await callback.message.answer("Отправьте сообщение для клиента:", reply_markup=kb.cancel_kb())
    await callback.answer()


@router.message(AdminMessageFSM.waiting_message)
async def admin_message_client_send(message: Message, state: FSMContext):
    await message.bot.copy_message(chat_id=CLIENT_ID, from_chat_id=message.chat.id, message_id=message.message_id)
    await state.clear()
    await message.answer("Сообщение отправлено", reply_markup=kb.back_to_menu_kb("admin"))
