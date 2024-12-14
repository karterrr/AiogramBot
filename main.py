import logging
import sys
import asyncio

from aiogram import Bot, Dispatcher

from app.handlers import router
from app.database import db_start
from bot_token import bot_token



async def on_startup():
    await db_start()
    print('Бот успешно запущен!')


async def main():
    bot = Bot(bot_token)
    dp = Dispatcher()
    dp.include_router(router)
    await on_startup()
    await dp.start_polling(bot)



if __name__=='__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Бот выключен')
