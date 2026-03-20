import os
from fastapi import FastAPI
from fastapi.responses import FileResponse
from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo
from aiogram.filters import CommandStart
import uvicorn
import asyncio

# Конфигурация
TOKEN = os.getenv("BOT_TOKEN")
# URL будет получен после деплоя на Render
APP_URL = os.getenv("APP_URL") 

app = FastAPI()
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Отдача HTML-файла
@app.get("/")
async def read_index():
    return FileResponse('index.html')

# Хендлер команды /start
@dp.message(CommandStart())
async def start(message: types.Message):
    markup = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Открыть приложение", web_app=WebAppInfo(url=APP_URL))]
        ],
        resize_keyboard=True
    )
    await message.answer("Нажми на кнопку ниже, чтобы запустить Mini App!", reply_markup=markup)

# Запуск бота через FastAPI (хук)
@app.on_event("startup")
async def on_startup():
    asyncio.create_task(dp.start_polling(bot))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
