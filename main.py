import os
import asyncio
import random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo
from aiogram.filters import CommandStart
import uvicorn

app = FastAPI()
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Состояние игры
game_state = {
    "timer": 30,
    "total_pot": 0,
    "players": [], # {id, name, bet, color}
    "history": []
}

active_connections = []

async def game_loop():
    while True:
        if game_state["timer"] > 0:
            game_state["timer"] -= 1
        else:
            if game_state["total_pot"] > 0:
                # Розыгрыш
                winner = pick_winner()
                prize = game_state["total_pot"] * 0.95 # 5% комиссия
                result = {
                    "type": "result",
                    "winner": winner,
                    "prize": prize,
                    "total_pot": game_state["total_pot"]
                }
                game_state["history"].insert(0, {"winner": winner['name'], "pot": game_state["total_pot"]})
                game_state["history"] = game_state["history"][:10] # Храним последние 10
                await broadcast(result)
                await asyncio.sleep(7) # Пауза на показ анимации
            
            # Сброс
            game_state["timer"] = 30
            game_state["total_pot"] = 0
            game_state["players"] = []
            await broadcast({"type": "sync", "state": game_state})
        
        await broadcast({"type": "timer", "value": game_state["timer"]})
        await asyncio.sleep(1)

def pick_winner():
    r = random.uniform(0, game_state["total_pot"])
    current = 0
    for p in game_state["players"]:
        current += p["bet"]
        if r <= current:
            return p
    return game_state["players"][0]

async def broadcast(data):
    for connection in active_connections:
        try:
            await connection.send_json(data)
        except:
            active_connections.remove(connection)

@app.get("/")
async def get():
    return FileResponse('index.html')

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    # Сразу синхронизируем состояние
    await websocket.send_json({"type": "sync", "state": game_state})
    try:
        while True:
            data = await websocket.receive_json()
            if data["type"] == "bet":
                new_player = {
                    "id": data["id"],
                    "name": data["name"],
                    "bet": data["amount"],
                    "color": data["color"]
                }
                game_state["players"].append(new_player)
                game_state["total_pot"] += data["amount"]
                await broadcast({"type": "sync", "state": game_state})
    except WebSocketDisconnect:
        active_connections.remove(websocket)

@dp.message(CommandStart())
async def start(message: types.Message):
    markup = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="Играть", web_app=WebAppInfo(url=os.getenv("APP_URL")))]],
        resize_keyboard=True
    )
    await message.answer("Входи в игру!", reply_markup=markup)

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(dp.start_polling(bot))
    asyncio.create_task(game_loop())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))

