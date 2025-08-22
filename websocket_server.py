import asyncio
import json
import uuid
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List
import random

app = FastAPI()

# Хранилище игровых комнат
game_rooms: Dict[str, dict] = {}
connections: Dict[str, WebSocket] = {}

class GameManager:
    def __init__(self):
        self.rooms = {}
    
    async def create_room(self, websocket: WebSocket, player_name: str):
        """Создать новую игровую комнату"""
        room_code = str(random.randint(1000, 9999))
        
        # Убеждаемся что код уникален
        while room_code in self.rooms:
            room_code = str(random.randint(1000, 9999))
        
        player_id = str(uuid.uuid4())
        
        self.rooms[room_code] = {
            "room_code": room_code,
            "players": {
                player_id: {
                    "name": player_name,
                    "websocket": websocket,
                    "ready": False,
                    "answers": {}
                }
            },
            "game_state": "waiting",  # waiting, playing, finished
            "current_question": 0,
            "questions": [
                {
                    "id": 1,
                    "question": "Какой фрукт выберет ваш партнер?",
                    "options": [
                        {"id": "apple", "name": "Яблоко", "emoji": "🍎"},
                        {"id": "banana", "name": "Банан", "emoji": "🍌"},
                        {"id": "strawberry", "name": "Клубника", "emoji": "🍓"},
                        {"id": "orange", "name": "Апельсин", "emoji": "🍊"}
                    ]
                },
                {
                    "id": 2,
                    "question": "Какой цвет больше нравится партнеру?",
                    "options": [
                        {"id": "red", "name": "Красный", "emoji": "❤️"},
                        {"id": "blue", "name": "Синий", "emoji": "💙"},
                        {"id": "green", "name": "Зеленый", "emoji": "💚"},
                        {"id": "yellow", "name": "Желтый", "emoji": "💛"}
                    ]
                }
            ],
            "created_at": datetime.now().isoformat()
        }
        
        await self.send_to_player(websocket, {
            "type": "room_created",
            "room_code": room_code,
            "player_id": player_id
        })
        
        return room_code, player_id
    
    async def join_room(self, websocket: WebSocket, room_code: str, player_name: str):
        """Присоединиться к комнате"""
        if room_code not in self.rooms:
            await self.send_to_player(websocket, {
                "type": "error",
                "message": "Комната не найдена"
            })
            return None, None
        
        room = self.rooms[room_code]
        
        if len(room["players"]) >= 2:
            await self.send_to_player(websocket, {
                "type": "error", 
                "message": "Комната переполнена"
            })
            return None, None
        
        player_id = str(uuid.uuid4())
        room["players"][player_id] = {
            "name": player_name,
            "websocket": websocket,
            "ready": False,
            "answers": {}
        }
        
        # Уведомляем всех в комнате
        await self.broadcast_to_room(room_code, {
            "type": "player_joined",
            "player_name": player_name,
            "players_count": len(room["players"])
        })
        
        await self.send_to_player(websocket, {
            "type": "room_joined",
            "room_code": room_code,
            "player_id": player_id
        })
        
        return room_code, player_id
    
    async def start_game(self, room_code: str):
        """Начать игру"""
        room = self.rooms[room_code]
        room["game_state"] = "playing"
        room["current_question"] = 0
        
        question = room["questions"][0]
        
        await self.broadcast_to_room(room_code, {
            "type": "game_started",
            "question": question
        })
    
    async def submit_answer(self, room_code: str, player_id: str, answer: str):
        """Отправить ответ"""
        room = self.rooms[room_code]
        current_q = room["current_question"]
        
        room["players"][player_id]["answers"][current_q] = answer
        
        # Проверяем, ответили ли все
        answered_count = sum(1 for p in room["players"].values() 
                           if current_q in p["answers"])
        
        await self.broadcast_to_room(room_code, {
            "type": "answer_received",
            "player_id": player_id,
            "answered_count": answered_count,
            "total_players": len(room["players"])
        })
        
        # Если все ответили
        if answered_count == len(room["players"]):
            await self.show_results(room_code, current_q)
    
    async def show_results(self, room_code: str, question_index: int):
        """Показать результаты раунда"""
        room = self.rooms[room_code]
        
        # Собираем ответы
        answers = {}
        for pid, player in room["players"].items():
            answers[pid] = {
                "name": player["name"],
                "answer": player["answers"][question_index]
            }
        
        await self.broadcast_to_room(room_code, {
            "type": "round_results",
            "answers": answers
        })
        
        # Переходим к следующему вопросу или завершаем игру
        await asyncio.sleep(3)  # Показываем результаты 3 секунды
        
        if question_index + 1 < len(room["questions"]):
            room["current_question"] += 1
            next_question = room["questions"][room["current_question"]]
            
            await self.broadcast_to_room(room_code, {
                "type": "next_question",
                "question": next_question
            })
        else:
            await self.finish_game(room_code)
    
    async def finish_game(self, room_code: str):
        """Завершить игру"""
        room = self.rooms[room_code]
        room["game_state"] = "finished"
        
        # Подсчитываем совпадения
        total_questions = len(room["questions"])
        matches = 0
        
        for q_index in range(total_questions):
            answers = [p["answers"][q_index] for p in room["players"].values()]
            if len(set(answers)) == 1:  # Все ответы одинаковые
                matches += 1
        
        compatibility = round((matches / total_questions) * 100)
        
        # Генерируем совет от гномов
        if compatibility >= 75:
            gnome_advice = "Гном-Купидон в восторге! Вы понимаете друг друга с полуслова!"
        elif compatibility >= 50:
            gnome_advice = "Гном-Мудрец кивает: хорошее взаимопонимание, есть куда расти!"
        else:
            gnome_advice = "Гном-Исследователь предлагает: больше узнавайте друг о друге!"
        
        await self.broadcast_to_room(room_code, {
            "type": "game_finished",
            "compatibility": compatibility,
            "matches": matches,
            "total": total_questions,
            "gnome_advice": gnome_advice
        })
    
    async def send_to_player(self, websocket: WebSocket, message: dict):
        """Отправить сообщение одному игроку"""
        try:
            await websocket.send_text(json.dumps(message))
        except:
            pass
    
    async def broadcast_to_room(self, room_code: str, message: dict):
        """Отправить сообщение всем в комнате"""
        if room_code not in self.rooms:
            return
        
        room = self.rooms[room_code]
        for player in room["players"].values():
            await self.send_to_player(player["websocket"], message)

# Глобальный менеджер игр
game_manager = GameManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "create_room":
                await game_manager.create_room(
                    websocket, 
                    message["player_name"]
                )
            
            elif message["type"] == "join_room":
                await game_manager.join_room(
                    websocket,
                    message["room_code"], 
                    message["player_name"]
                )
            
            elif message["type"] == "start_game":
                await game_manager.start_game(message["room_code"])
            
            elif message["type"] == "submit_answer":
                await game_manager.submit_answer(
                    message["room_code"],
                    message["player_id"],
                    message["answer"]
                )
    
    except WebSocketDisconnect:
        # Обработка отключения
        pass
