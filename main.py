import logging
import sys
import asyncio

from aiogram import Bot, Dispatcher

from app.handlers.user_handlers import router
from app.handlers.admin_handlers import admin_router, AdminCheckMiddleware
from app.database import db_start
from bot_token import bot_token



async def on_startup():
    await db_start()
    print('Бот успешно запущен!')

async def on_shutdown(bot: Bot):
    print("Бот завершает работу...")
    await bot.session.close()


async def main():
    bot = Bot(bot_token)
    dp = Dispatcher()

    admin_router.message.middleware(AdminCheckMiddleware())

    dp.include_router(router)
    dp.include_router(admin_router)

    await on_startup()
    try:
        await dp.start_polling(bot)
    finally:
        await on_shutdown(bot)




if __name__=='__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Бот выключен')
