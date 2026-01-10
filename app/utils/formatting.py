import re


_MD_RE = re.compile(r"([_\*\[\]()~`>#+\-=|{}.!])")


def md_escape(text: str | None) -> str:
    if text is None:
        return ""
    return _MD_RE.sub(r"\\\1", str(text))


def status_label(status: str | None) -> str:
    mapping = {
        "pending": "⏳ ожидание",
        "approved": "✅ одобрено",
        "rejected": "❌ отклонено",
        "done": "✅ выполнено",
    }
    return mapping.get(status or "", md_escape(status or ""))


def delivery_label(delivery: str | None) -> str:
    if delivery == "manual":
        return "🧾 вручную"
    return "🧾 вручную"


def limit_label(limit: int | None) -> str:
    return "без ограничений" if not limit else str(limit)


def format_price_lines(prices: list[dict]) -> str:
    if not prices:
        return "—"
    lines: list[str] = []
    for p in prices:
        lines.append(
            f"• {p['amount']} {md_escape(p.get('currency_icon', ''))} {md_escape(p.get('currency_name', ''))}"
        )
    return "\n".join(lines)


def format_balance(rows) -> str:
    lines = ["*Ваш баланс*"]
    for row in rows:
        lines.append(
            f"• {md_escape(row.currency.icon)} {md_escape(row.currency.name)}: *{row.amount}*"
        )
    return "\n".join(lines)


def format_gift_card(details: dict) -> str:
    name = md_escape(details.get("name", ""))
    description = md_escape(details.get("description", ""))
    delivery = delivery_label(details.get("delivery"))
    limit = limit_label(details.get("max_orders"))
    prices = format_price_lines(details.get("prices", []))

    lines = [f"*{name}*"]
    if description:
        lines.append(f"_{description}_")
    lines.append(f"*Тип:* {delivery}")
    lines.append(f"*Лимит:* {md_escape(limit)}")
    lines.append("*Цена:*")
    lines.append(prices)
    return "\n".join(lines)


def format_order_admin(order_id: int, gift_name: str, client_id: int, status: str, prices: list[dict], auto_note: bool) -> str:
    lines = [
        f"*Новый заказ* \\#{order_id}",
        f"*Подарок:* {md_escape(gift_name)}",
        f"*Клиент:* `{client_id}`",
        f"*Статус:* {status_label(status)}",
        "*Цена:*",
        format_price_lines(prices),
    ]
    if auto_note:
        lines.append("_Выдан автоматически_")
    return "\n".join(lines)


def format_order_client(order_id: int, gift_name: str, status: str, created_at: str) -> str:
    return "\n".join(
        [
            f"*Заказ* \\#{order_id}",
            f"*Подарок:* {md_escape(gift_name)}",
            f"*Статус:* {status_label(status)}",
            f"*Время:* {md_escape(created_at)}",
        ]
    )


def format_request_client(request_id: int, currency_icon: str, currency_name: str, comment: str, status: str, created_at: str) -> str:
    return "\n".join(
        [
            f"*Заявка* \\#{request_id}",
            f"*Валюта:* {md_escape(currency_icon)} {md_escape(currency_name)}",
            f"*Комментарий:* {md_escape(comment)}",
            f"*Статус:* {status_label(status)}",
            f"*Время:* {md_escape(created_at)}",
        ]
    )
