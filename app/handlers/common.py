from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import app.keyboards as kb

router = Router()


@router.message(CommandStart())
async def start(message: Message, role: str):
    await message.answer("Главное меню", reply_markup=kb.menu_kb(role))


@router.message(Command("menu"))
async def menu_cmd(message: Message, role: str):
    await message.answer("Главное меню", reply_markup=kb.menu_kb(role))


@router.callback_query(F.data.startswith("menu:"))
async def menu_callback(callback: CallbackQuery, role: str):
    target = callback.data.split(":", 1)[1]
    if target != role:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.answer("Главное меню", reply_markup=kb.menu_kb(role))
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext, role: str):
    await state.clear()
    await callback.message.answer("Действие отменено", reply_markup=kb.back_to_menu_kb(role))
    await callback.answer()
