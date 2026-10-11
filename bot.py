import asyncio
import os
import sqlite3
from datetime import date
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton)

bot = Bot(token=os.environ["BOT_TOKEN"])
dp = Dispatcher()

CATEGORIES = ["yolkira", "ovqatlanish", "bozorlik", "boshqalar"]

db = sqlite3.connect("expenses.db")
db.execute("""CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    category TEXT,
    amount INTEGER,
    day TEXT)""")
db.commit()

class Expense(StatesGroup):
    amount = State()

def categories_kb():
    rows = [[InlineKeyboardButton(text=c, callback_data=f"cat:{c}")]
            for c in CATEGORIES]
    return InlineKeyboardMarkup(inline_keyboard=rows)

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("Выберите категорию:", reply_markup=categories_kb())

@dp.message(Command("today"))
async def today(message: Message):
    rows = db.execute(
        "SELECT category, SUM(amount) FROM expenses "
        "WHERE user_id = ? AND day = ? GROUP BY category",
        (message.from_user.id, date.today().isoformat())).fetchall()
    if not rows:
        await message.answer("Сегодня расходов нет.")
        return
    total = sum(r[1] for r in rows)
    lines = [f"{c}: {s}" for c, s in rows]
    await message.answer("Сегодня:\n" + "\n".join(lines) + f"\nИтого: {total}")

@dp.callback_query(F.data.startswith("cat:"))
async def choose_category(call: CallbackQuery, state: FSMContext):
    category = call.data.split(":")[1]
    await state.update_data(category=category)
    await state.set_state(Expense.amount)
    await call.message.answer(f"Категория: {category}. Введите сумму:")
    await call.answer()

@dp.message(Expense.amount)
async def get_amount(message: Message, state: FSMContext):
    text = (message.text or "").replace(" ", "")
    if not text.isdigit():
        await message.answer("Введите сумму числом, например 25000")
        return
    data = await state.get_data()
    await state.clear()
    db.execute(
        "INSERT INTO expenses (user_id, category, amount, day) "
        "VALUES (?, ?, ?, ?)",
        (message.from_user.id, data["category"], int(text),
         date.today().isoformat()))
    db.commit()
    await message.answer(f"Записано: {data['category']}, {int(text)}")
    await message.answer("Выберите категорию:", reply_markup=categories_kb())

@dp.message(Command("week"))
async def week(message: Message):
    rows = db.execute(
        "SELECT category, SUM(amount) FROM expenses "
        "WHERE user_id = ? "
        "AND day >= date('now', 'localtime', '-6 days') "
        "GROUP BY category",
        (message.from_user.id,)).fetchall()
    if not rows:
        await message.answer("За 7 дней расходов нет.")
        return
    total = sum(r[1] for r in rows)
    lines = [f"{c}: {s}" for c, s in rows]
    await message.answer("За 7 дней:\n" + "\n".join(lines)
                         + f"\nИтого: {total}")

async def main():
    await dp.start_polling(bot)

asyncio.run(main())
