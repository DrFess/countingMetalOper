import json

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, WebAppInfo, KeyboardButton, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from requests import Session

from settings import WEB_APP_URL, LOGIN, PASSWORD, headers_auth, headers_L2_plan_operations
from utils.check_history_number import check_history_number, check_for_protocols
from utils.create_protocols import create_protocols_func
from utils.l2_requests import get_operation_plan, authorization_L2

router = Router()


class Scanning(StatesGroup):
    history_number_step = State()
    prescan_step = State()


@router.message(F.text == 'Добавить медицинское изделие')
async def get_history_numbers(message: Message):
    """План операций"""
    session = Session()
    authorization_L2(connect=session, login=LOGIN, password=PASSWORD, headers=headers_auth)
    if get_operation_plan(connect=session, headers=headers_L2_plan_operations):
        operation_plan = get_operation_plan(connect=session, headers=headers_L2_plan_operations).get('result')
    else:
        operation_plan = [{'direction': 'План операций не найден'}]
    builder = InlineKeyboardBuilder()
    for item in operation_plan:
        builder.row(InlineKeyboardButton(text=item.get('direction'), callback_data=f"historyNumber_{item.get('direction')}"))
    builder.row(InlineKeyboardButton(text='Ввести номер истории', callback_data='historyNumber_manual'))
    await message.answer('План операций', reply_markup=builder.as_markup())


@router.callback_query(F.data.contains('historyNumber'))
async def start_scanning_handler(callback: CallbackQuery, state: FSMContext):
    """Ветвление в зависимости от номера истории"""
    data = callback.data
    history_number = data.split('_')[1]
    if history_number == 'manual':
        await state.set_state(Scanning.history_number_step)
        await callback.message.answer('Отправь номер истории')
    else:
        await state.set_state(Scanning.prescan_step)
        await state.update_data(history_number=history_number)
        builder = ReplyKeyboardBuilder()
        builder.row(KeyboardButton(text='QR/Barcode scanner', web_app=WebAppInfo(url=WEB_APP_URL)))
        await callback.message.answer('Запустить сканер?', reply_markup=builder.as_markup(resize_keyboard=True, one_time_keyboard=True))


@router.message(Scanning.history_number_step)
async def start_scanning_handler(message: Message, state: FSMContext):
    """Обработчик для историй вне плана операций"""
    await state.update_data(history_number=message.text)

    if check_history_number(message.text):
        await state.set_state(Scanning.prescan_step)
        builder = ReplyKeyboardBuilder()
        builder.row(KeyboardButton(text='QR/Barcode scanner', web_app=WebAppInfo(url=WEB_APP_URL)))
        await message.answer('Запустить сканер?', reply_markup=builder.as_markup(resize_keyboard=True, one_time_keyboard=True))

    else:
        await state.clear()
        builder = ReplyKeyboardBuilder()
        builder.row(KeyboardButton(text='Начать сканирование'))
        await message.answer('Проверь номер истории и начни снова', reply_markup=builder.as_markup())


@router.message(F.web_app_data, Scanning.prescan_step)
async def qr_scanner_handler(message: Message, state: FSMContext):
    """Обработчик данных от QR сканера"""

    scanner_data = json.loads(message.web_app_data.data)
    data_for_protocol = scanner_data.get('qr_data')
    data = await state.get_data()
    history_number = data.get('history_number')
    checking = check_for_protocols(history_number=history_number)
    if not checking:
        try:
            create_protocols_func(history_number)
        except Exception as error:
            await message.answer(f'При добавлении предоперационного осмотра или протокола операции возникла ошибка: {error}')
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text='Добавить медицинское изделие'))
    builder.row(KeyboardButton(text='Результаты из базы данных'))
    await message.answer(
        f'Результат сканирования: {data_for_protocol} добавлен в протокол операции',
        reply_markup=builder.as_markup(resize_keyboard=True, one_time_keyboard=True)
    )
    await state.clear()
