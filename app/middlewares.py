from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from config import ADMIN_ID, CLIENT_ID


class RoleMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id

        role = None
        if user_id == ADMIN_ID:
            role = "admin"
        elif user_id == CLIENT_ID:
            role = "client"

        if role:
            data["role"] = role
            return await handler(event, data)

        if isinstance(event, Message):
            await event.answer(
                "🚫 У вас нет доступа к боту, отправьте свой Tg ID администратору."
            )
        elif isinstance(event, CallbackQuery):
            await event.message.answer(
                "🚫 У вас нет доступа к боту, отправьте свой Tg ID администратору."
            )
            await event.answer()
