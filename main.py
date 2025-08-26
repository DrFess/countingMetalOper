import asyncio
import logging

from aiogram import Bot, Router, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command
from aiogram.types import Message, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from handlers import scanning_handler
from settings import BOT_TOKEN, PROXY_URL

session = AiohttpSession(proxy=PROXY_URL)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'), session=session)
# bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))  # для запуска на ноуте

router = Router()


@router.message(Command(commands=['start', 'menu']))
async def command_start_handler(message: Message):
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text='Добавить медицинское изделие'))
    builder.row(KeyboardButton(text='Результаты из базы данных'))
    await message.answer('Добро пожаловать!', reply_markup=builder.as_markup(resize_keyboard=True, one_time_keyboard=True))


async def main():
    dp = Dispatcher()
    dp.include_routers(
        router,
        scanning_handler.router,
    )
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
