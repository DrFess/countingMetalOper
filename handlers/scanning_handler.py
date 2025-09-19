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
    counting_step = State()
    finished_step = State()


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
        history_number = item.get('direction')
        surname_patient = item.get('fio_patient')
        surname_patient_list = surname_patient.split(' ')
        fio_patient = '.'.join([surname_patient_list[0][0], surname_patient_list[1]])
        builder.row(InlineKeyboardButton(text=f'{history_number} - {fio_patient}', callback_data=f'historyNumber_{history_number}'))
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
    await state.update_data(metal_info=data_for_protocol)
    await message.answer(text=f'Результат сканирования: {data_for_protocol})\n\n'
                              f'Укажите количество установленных конструкций\n\n'
                              f'\u2757 ВАЖНО \u2757 Отправить нужно только цифру, никаких других символов\u2757')
    await state.set_state(Scanning.counting_step)


@router.message(Scanning.counting_step)
async def get_count_data(message: Message, state: FSMContext):
    """Обработчик сообщения о количестве изделий"""
    metal_count = message.text
    if metal_count.isdigit():
        await state.update_data(count=metal_count)
        data = await state.get_data()
        history_number = data.get('history_number')
        data_for_protocol = data.get('metal_info')
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text=f'Верно, добавить протоколы', callback_data='true'))
        builder.row(InlineKeyboardButton(text=f'Ошибка, исправить', callback_data='false'))
        await message.answer(text=f'История болезни: {history_number}\n'
                                  f'Имплантированное изделие: {data_for_protocol}\n'
                                  f'Количество: {metal_count}', reply_markup=builder.as_markup())
        await state.set_state(Scanning.finished_step)
    else:
        await message.answer(text=f'В сообщение {metal_count} указаны отличные от цифр символы\n\n'
                                  f'Укажите количество установленных конструкций\n\n'
                                  f'\u2757 ВАЖНО \u2757 Отправить нужно только цифру, никаких других символов\u2757'
                             )


@router.callback_query(F.data.contains('true'), Scanning.finished_step)
async def create_protocols_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик создания протокола (финальный этап)"""
    data = await state.get_data()
    history_number = data.get('history_number')
    data_for_protocol = data.get('metal_info')
    metal_count = data.get('count')
    checking = check_for_protocols(history_number=history_number)
    if not checking:
        try:
            create_protocols_func(history_number, data_for_protocol, metal_count)
        except Exception as error:
            await callback.message.answer(
                f'При добавлении предоперационного осмотра или протокола операции возникла ошибка: {error}')
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text='Добавить медицинское изделие'))
    builder.row(KeyboardButton(text='Результаты из базы данных'))
    await callback.message.answer(
        'Предоперационный протокол и протокол операции созданы. Данные о конструкции добавлены в протокол операции',
        reply_markup=builder.as_markup(resize_keyboard=True, one_time_keyboard=True)
    )
    await state.clear()


@router.callback_query(F.data.contains('false'), Scanning.finished_step)
async def wrong_data_handler(callback: CallbackQuery, state: FSMContext):
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text='Добавить медицинское изделие'))
    builder.row(KeyboardButton(text='Результаты из базы данных'))
    await callback.message.answer('Вы указали, что данные ошибочные. Начните процесс добавления конструкции заново',
                                  reply_markup=builder.as_markup(resize_keyboard=True, one_time_keyboard=True)
                                  )
    await state.clear()
