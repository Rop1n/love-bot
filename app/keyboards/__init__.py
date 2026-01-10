from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def cancel_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]]
    )


def menu_kb(role: str):
    if role == "admin":
        buttons = [
            [InlineKeyboardButton(text="💰 Валюты", callback_data="admin:currencies")],
            [InlineKeyboardButton(text="💐 Подарки", callback_data="admin:gifts")],
            [InlineKeyboardButton(text="📝 Заявки на валюту", callback_data="admin:currency_requests")],
            [InlineKeyboardButton(text="✅ Заказы на подарки", callback_data="admin:gift_orders")],
            [InlineKeyboardButton(text="💳 Баланс клиента", callback_data="admin:client_balance")],
            [InlineKeyboardButton(text="➕ Начислить валюту", callback_data="admin:grant_currency")],
            [InlineKeyboardButton(text="📥 Импорт подарков", callback_data="admin:import_gifts")],
            [InlineKeyboardButton(text="✉️ Сообщение клиенту", callback_data="admin:message_client")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    buttons = [
        [InlineKeyboardButton(text="💰 Мои валюты", callback_data="client:balance")],
        [InlineKeyboardButton(text="🎁 Каталог подарков", callback_data="client:gifts")],
        [InlineKeyboardButton(text="📝 Запросить валюту", callback_data="client:request_currency")],
        [InlineKeyboardButton(text="📋 Мои заявки", callback_data="client:requests")],
        [InlineKeyboardButton(text="⏳ Мои заказы", callback_data="client:orders")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_to_menu_kb(role: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="↩️ В меню", callback_data=f"menu:{role}")]]
    )


def admin_currency_menu_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать валюту", callback_data="currency:new")],
            [InlineKeyboardButton(text="✏️ Редактировать валюты", callback_data="currency:list")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="menu:admin")],
        ]
    )


def admin_gift_menu_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать подарок", callback_data="gift:new")],
            [InlineKeyboardButton(text="✏️ Редактировать подарки", callback_data="gift:list")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="menu:admin")],
        ]
    )


def currency_open_edit_kb(currency_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"currency:open:{currency_id}")]
        ]
    )


def currency_edit_kb(currency_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Имя", callback_data=f"currency:edit:{currency_id}:name")],
            [InlineKeyboardButton(text="🌟 Иконка", callback_data=f"currency:edit:{currency_id}:icon")],
            [InlineKeyboardButton(text="📖 Описание", callback_data=f"currency:edit:{currency_id}:description")],
            [InlineKeyboardButton(text="⏳ Лимит в день", callback_data=f"currency:edit:{currency_id}:daily_limit")],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"currency:delete:{currency_id}")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="currency:list")],
        ]
    )


def currencies_kb(currencies: list, prefix: str, include_cancel: bool = True):
    builder = InlineKeyboardBuilder()
    for c in currencies:
        builder.button(text=f"{c.icon} {c.name}", callback_data=f"{prefix}:{c.id}")
    if include_cancel:
        builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)
    return builder.as_markup()


def confirm_prices_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить валюту", callback_data="gift:price:add")],
            [InlineKeyboardButton(text="✅ Сохранить", callback_data="gift:save")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
        ]
    )


def gift_list_item_kb(gift_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"gift:open:{gift_id}")]]
    )


def gift_edit_kb(gift_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Имя", callback_data=f"gift:edit:{gift_id}:name")],
            [InlineKeyboardButton(text="📝 Описание", callback_data=f"gift:edit:{gift_id}:description")],
            [InlineKeyboardButton(text="🔢 Лимит", callback_data=f"gift:edit:{gift_id}:limit")],
            [InlineKeyboardButton(text="💰 Цена", callback_data=f"gift:prices:{gift_id}")],
            [InlineKeyboardButton(text="📦 Контент", callback_data=f"gift:content:{gift_id}")],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"gift:delete:{gift_id}")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="gift:list")],
        ]
    )


def gift_delivery_kb(gift_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧾 Вручную", callback_data=f"gift:delivery:{gift_id}:manual")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data=f"gift:open:{gift_id}")],
        ]
    )


def gift_create_delivery_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧾 Вручную", callback_data="gift:new_delivery:manual")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
        ]
    )


def gift_content_kb(gift_id: int, has_content: bool):
    buttons = [[InlineKeyboardButton(text="📤 Загрузить/обновить", callback_data=f"gift:content:set:{gift_id}")]]
    if has_content:
        buttons.append([InlineKeyboardButton(text="🗑 Очистить", callback_data=f"gift:content:clear:{gift_id}")])
    buttons.append([InlineKeyboardButton(text="↩️ Назад", callback_data=f"gift:open:{gift_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def gift_price_list_kb(gift_id: int, prices: list[dict]):
    buttons: list[list[InlineKeyboardButton]] = []
    for p in prices:
        buttons.append([
            InlineKeyboardButton(
                text=f"✏ {p['currency_icon']} {p['currency_name']} — {p['amount']}",
                callback_data=f"gift:price:edit:{p['id']}"
            ),
            InlineKeyboardButton(
                text=f"🗑 {p['currency_icon']}",
                callback_data=f"gift:price:delete:{p['id']}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="➕ Добавить цену", callback_data=f"gift:price:add:{gift_id}")
    ])
    buttons.append([
        InlineKeyboardButton(text="↩️ Назад", callback_data=f"gift:open:{gift_id}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def gift_price_currency_kb(gift_id: int, currencies: list):
    builder = InlineKeyboardBuilder()
    for c in currencies:
        builder.button(text=f"{c.icon} {c.name}", callback_data=f"gift:price:currency:{gift_id}:{c.id}")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)
    return builder.as_markup()


def client_gift_kb(gift_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🛒 Купить", callback_data=f"client:buy:{gift_id}")]]
    )


def admin_request_kb(request_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"request:approve:{request_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"request:reject:{request_id}")
        ]]
    )


def admin_order_kb(order_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Исполнено", callback_data=f"order:done:{order_id}")],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"order:reject:{order_id}")],
            [InlineKeyboardButton(text="✉️ Отправить контент", callback_data=f"order:send:{order_id}")],
        ]
    )
