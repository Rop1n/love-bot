import asyncio
from aiogram import Bot, Dispatcher
from config import TOKEN, ADMIN_ID, CLIENT_ID
from app.middlewares import RoleMiddleware
from app.handlers import router
from app.database.models import async_main
from app.database.requests import ensure_users


async def main():
    await async_main()
    await ensure_users(ADMIN_ID, CLIENT_ID)
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    dp.message.middleware(RoleMiddleware())
    dp.callback_query.middleware(RoleMiddleware())
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("exit")
