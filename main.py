import os
import json
import random
import logging
import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Gnome Horoscope API",
    version="2.0.0",
    description="🧙‍♂️ API для мини-приложения Гномий Гороскоп"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ МОДЕЛИ ============
class FavoriteRequest(BaseModel):
    initData: str = ""
    type: str
    content: Any

class CreateRoomRequest(BaseModel):
    game_type: str
    creator_name: str
    initData: str = ""

class JoinRoomRequest(BaseModel):
    room_id: str
    player_name: str
    initData: str = ""

class AnswerRequest(BaseModel):
    room_id: str
    player_name: str
    question_id: int
    answer: str
    initData: str = ""

# ============ WEBSOCKET МЕНЕДЖЕР ============
class GameConnectionManager:
    def __init__(self):
        self.room_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, room_id: str, websocket: WebSocket):
        await websocket.accept()
        if room_id not in self.room_connections:
            self.room_connections[room_id] = []
        self.room_connections[room_id].append(websocket)
        logger.info(f"🔗 WebSocket подключен к комнате {room_id}")
        
        # Уведомляем всех в комнате о новом подключении
        await self.broadcast_to_room(room_id, {
            "type": "player_joined",
            "players_count": len(self.room_connections[room_id])
        })
    
    async def disconnect(self, room_id: str, websocket: WebSocket):
        if room_id in self.room_connections:
            if websocket in self.room_connections[room_id]:
                self.room_connections[room_id].remove(websocket)
            
            if not self.room_connections[room_id]:
                del self.room_connections[room_id]
            else:
                await self.broadcast_to_room(room_id, {
                    "type": "player_left",
                    "players_count": len(self.room_connections[room_id])
                })
    
    async def broadcast_to_room(self, room_id: str, message: dict):
        if room_id in self.room_connections:
            dead_connections = []
            
            for connection in self.room_connections[room_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"WebSocket error: {e}")
                    dead_connections.append(connection)
            
            # Удаляем мертвые соединения
            for dead in dead_connections:
                self.room_connections[room_id].remove(dead)

connection_manager = GameConnectionManager()

# ============ ДАННЫЕ ============
HOROSCOPE_TEMPLATES = [
    "Звезды советуют вам проявить инициативу! Сегодня удачный день для новых начинаний.",
    "Прислушайтесь к своей интуиции - она не подведет в важных решениях.",
    "День благоприятен для общения и установления новых контактов.",
    "Сосредоточьтесь на семейных делах, близкие нуждаются в вашей поддержке.",
    "Время проявить творческие способности! Не бойтесь экспериментировать.",
    "Практичный подход к делам принесет отличные результаты.",
    "Ищите баланс во всем - работе, отдыхе и отношениях.",
    "Глубокий анализ ситуации поможет найти неожиданное решение.",
    "Расширьте горизонты! Новые знания откроют перспективы.",
    "Терпение и настойчивость - ключ к достижению цели.",
    "Время для смелых идей и нестандартных решений!",
    "Доверьтесь течению жизни, интуиция подскажет верный путь."
]

DAY_CARDS = [
    {"название": "Гном-авантюрист", "совет": "Сегодня время для смелых решений! Не бойся рискнуть - фортуна любит храбрых."},
    {"название": "Гном-повар", "совет": "День для заботы о своем теле и душе. Приготовь что-то вкусное или побалуй себя."},
    {"название": "Гном-садовник", "совет": "Время посадить семена будущих успехов. Небольшие действия сегодня принесут большие плоды."},
    {"название": "Гном-изобретатель", "совет": "Креативность зашкаливает сегодня! Придумай что-то новое или реши задачу нестандартным способом."},
    {"название": "Гном-музыкант", "совет": "Найди свой ритм дня. Включи любимую музыку и позволь мелодии вести тебя к успеху."},
    {"название": "Гном-философ", "совет": "Размышления принесут ясность. Уделите время анализу своих целей и желаний."},
    {"название": "Гном-путешественник", "совет": "Новые места и впечатления ждут! Даже короткая прогулка может стать приключением."},
    {"название": "Гном-мастер", "совет": "Руки помнят мудрость. Займитесь любимым делом или освойте новый навык."},
    {"название": "Гном-торговец", "совет": "День благоприятен для финансовых решений. Инвестируйте в свое будущее!"},
    {"название": "Гном-лекарь", "совет": "Позаботьтесь о своем здоровье. Небольшие изменения приведут к большим результатам."},
    {"название": "Гном-строитель", "совет": "Время закладывать фундамент новых проектов. Терпение принесет прочные результаты."},
    {"название": "Гном-звездочет", "совет": "Прислушайтесь к знакам Вселенной. Сегодня особенно важны интуиция и мечты."}
]

# ✅ ИСПРАВЛЕНО: Полные данные игр из questions.json
COUPLE_GAMES_DATA = {
    "fruit_game": [
        {
            "question": "Какой фрукт больше всего любит ваш партнер?",
            "options": ["🍎 Яблоко", "🍌 Банан", "🍊 Апельсин", "🍇 Виноград", "🥭 Манго", "🍓 Клубника"],
            "category": "taste"
        },
        {
            "question": "Какой экзотический фрукт хотел бы попробовать ваш партнер?",
            "options": ["🥥 Кокос", "🥝 Киви", "🍍 Ананас", "🥭 Манго", "🍈 Дыня", "🍑 Черешня"],
            "category": "taste"
        },
        {
            "question": "Какую ягоду предпочитает ваш партнер?",
            "options": ["🍓 Клубника", "🫐 Черника", "🍇 Виноград", "🍒 Вишня", "🍈 Крыжовник", "🍑 Малина"],
            "category": "taste"
        }
    ],
    "preference_test": [
        {
            "question": "Какой цвет больше всего нравится вашему партнеру?",
            "options": ["❤️ Красный", "💙 Синий", "💚 Зеленый", "💛 Желтый", "💜 Фиолетовый", "🖤 Черный"],
            "category": "colors"
        },
        {
            "question": "Какую музыку предпочитает ваш партнер?",
            "options": ["🎸 Рок", "🎵 Поп", "🎹 Классика", "🎺 Джаз", "🎤 Рэп", "🎻 Инди"],
            "category": "music"
        },
        {
            "question": "Какое время года любит ваш партнер?",
            "options": ["🌸 Весна", "☀️ Лето", "🍂 Осень", "❄️ Зима"],
            "category": "seasons"
        }
    ],
    "date_ideas": [
        {
            "question": "Идеальное свидание для вашего партнера:",
            "options": ["🎬 Кино", "🍽️ Ресторан", "🏞️ Прогулка в парке", "🏠 Дома с фильмом", "🎭 Театр", "🎪 Развлечения"],
            "category": "date_type"
        },
        {
            "question": "Какое время для свидания предпочитает партнер?",
            "options": ["🌅 Утро", "☀️ День", "🌆 Вечер", "🌙 Ночь"],
            "category": "date_time"
        }
    ]
}

# ============ ХРАНИЛИЩА ============
user_favorites = {}
game_rooms: Dict[str, Dict[str, Any]] = {}

# ✅ НОВОЕ: Кэш карт дня для детерминированной выдачи
daily_cards_cache = {}

# ============ ОСНОВНЫЕ РОУТЫ ============
@app.get("/")
async def root():
    return {
        "message": "🧙‍♂️ Gnome Horoscope API is running!",
        "status": "ok",
        "version": "2.0.0",
        "endpoints": [
            "GET /health",
            "GET /api/horoscope?sign=ЗНАК",
            "POST /api/day-card",
            "GET /api/favorites",
            "POST /api/favorites",
            "POST /api/create-room",
            "POST /api/join-room",
            "GET /api/room-status/{room_id}",
            "GET /api/game-question/{room_id}",
            "POST /api/submit-answer",
            "GET /api/game-results/{room_id}"
        ]
    }

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "Gnome Horoscope API",
        "rooms_count": len(game_rooms)
    }

@app.get("/api/horoscope")
async def get_horoscope(sign: str, date: str = None):
    try:
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        logger.info(f"Запрос гороскопа для {sign} на {date}")
        
        # ✅ Детерминированная генерация на основе знака и даты
        seed = hash(f"{sign}{date}") % len(HOROSCOPE_TEMPLATES)
        horoscope_text = HOROSCOPE_TEMPLATES[seed]
        
        return {
            "sign": sign,
            "date": date,
            "text": horoscope_text,
            "cached": False,
            "source": "Gnome Horoscope API"
        }
    except Exception as e:
        logger.error(f"Ошибка при получении гороскопа: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка при получении гороскопа")

@app.post("/api/day-card")
async def get_day_card(request: Dict[str, Any] = None):
    """✅ ИСПРАВЛЕНО: Детерминированная карта дня - одна карта на день"""
    try:
        logger.info("Запрос карты дня")
        
        # Получаем текущую дату
        current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        # Проверяем кэш
        if current_date in daily_cards_cache:
            card_data = daily_cards_cache[current_date]
            logger.info(f"📦 Карта дня из кэша для {current_date}")
        else:
            # Детерминированная генерация карты на основе даты
            date_seed = hash(current_date) % len(DAY_CARDS)
            selected_card = DAY_CARDS[date_seed]
            
            card_data = {
                "title": selected_card["название"],
                "text": selected_card["совет"],
                "reused": False,
                "date": current_date,
                "source": "Gnome Horoscope API"
            }
            
            # Сохраняем в кэш
            daily_cards_cache[current_date] = card_data
            logger.info(f"🆕 Новая карта дня для {current_date}: {selected_card['название']}")
        
        return card_data
        
    except Exception as e:
        logger.error(f"Ошибка при получении карты дня: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка при получении карты дня")

@app.get("/api/favorites")
async def get_favorites(initData: str = ""):
    try:
        user_id = initData or "anonymous"
        favorites = user_favorites.get(user_id, [])
        return {
            "favorites": favorites,
            "success": True,
            "message": "Избранное загружено",
            "count": len(favorites)
        }
    except Exception as e:
        logger.error(f"Ошибка при получении избранного: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка при получении избранного")

@app.post("/api/favorites")
async def add_favorite(request: FavoriteRequest):
    try:
        user_id = request.initData or "anonymous"
        if user_id not in user_favorites:
            user_favorites[user_id] = []
        
        favorite_item = {
            "type": request.type,
            "content": request.content,
            "added_at": datetime.now(timezone.utc).isoformat()
        }
        
        user_favorites[user_id].append(favorite_item)
        return {
            "success": True,
            "message": "Добавлено в избранное",
            "total_favorites": len(user_favorites[user_id])
        }
    except Exception as e:
        logger.error(f"Ошибка при добавлении в избранное: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка при добавлении в избранное")

# ============ ИСПРАВЛЕННЫЕ РОУТЫ ДЛЯ ИГР ============

@app.post("/api/create-room")
async def create_room(request: CreateRoomRequest):
    """✅ ИСПРАВЛЕНО: Создание игровой комнаты"""
    try:
        room_id = str(uuid.uuid4())[:8].upper()
        
        # Создаем комнату как словарь
        room = {
            "room_id": room_id,
            "created_at": datetime.now(timezone.utc),
            "players": [request.creator_name],
            "game_type": request.game_type,
            "current_question": 0,
            "answers": {},
            "status": "waiting"
        }
        
        game_rooms[room_id] = room
        logger.info(f"✅ Создана комната {room_id} для игры {request.game_type}")
        
        return {
            "success": True,
            "room_id": room_id,
            "message": f"Комната создана! Код: {room_id}",
            "game_type": request.game_type,
            "creator": request.creator_name
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания комнаты: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка создания комнаты")

@app.post("/api/join-room")
async def join_room(request: JoinRoomRequest):
    """✅ ИСПРАВЛЕНО: Присоединение к игровой комнате"""
    try:
        room = game_rooms.get(request.room_id)
        
        if not room:
            logger.warning(f"❌ Комната {request.room_id} не найдена")
            return {"success": False, "message": "Комната не найдена"}
        
        if len(room["players"]) >= 2:
            logger.warning(f"❌ Комната {request.room_id} полна")
            return {"success": False, "message": "Комната полна"}
        
        # Добавляем игрока, если его еще нет
        if request.player_name not in room["players"]:
            room["players"].append(request.player_name)
            logger.info(f"✅ Игрок {request.player_name} присоединился к комнате {request.room_id}")
        
        # Если два игрока - начинаем игру
        if len(room["players"]) == 2:
            room["status"] = "playing"
            logger.info(f"🎮 Игра началась в комнате {request.room_id}")
            
            # Уведомляем через WebSocket
            await connection_manager.broadcast_to_room(request.room_id, {
                "type": "game_started",
                "players": room["players"],
                "status": "playing"
            })
        
        return {
            "success": True,
            "message": "Присоединился к игре!" if len(room["players"]) == 2 else "Ожидаем второго игрока",
            "players": room["players"],
            "status": room["status"],
            "room_id": request.room_id
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка присоединения к комнате: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка присоединения к комнате")

@app.get("/api/room-status/{room_id}")
async def get_room_status(room_id: str):
    """Получить статус комнаты"""
    try:
        room = game_rooms.get(room_id)
        
        if not room:
            logger.warning(f"❌ Запрос статуса несуществующей комнаты: {room_id}")
            raise HTTPException(status_code=404, detail="Комната не найдена")
        
        return {
            "room_id": room_id,
            "players": room["players"],
            "status": room["status"],
            "current_question": room["current_question"],
            "player_count": len(room["players"]),
            "game_type": room["game_type"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка получения статуса комнаты: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка получения статуса")

@app.get("/api/game-question/{room_id}")
async def get_game_question(room_id: str):
    """✅ ИСПРАВЛЕНО: Получить текущий вопрос игры"""
    try:
        room = game_rooms.get(room_id)
        
        if not room:
            raise HTTPException(status_code=404, detail="Комната не найдена")
        
        # Получаем вопросы для типа игры
        game_questions = []
        if room["game_type"] == "mixed":
            # Смешанная игра - все типы вопросов
            for category in COUPLE_GAMES_DATA.values():
                game_questions.extend(category)
        else:
            game_questions = COUPLE_GAMES_DATA.get(room["game_type"], [])
        
        if not game_questions:
            logger.error(f"❌ Нет вопросов для типа игры: {room['game_type']}")
            raise HTTPException(status_code=500, detail="Нет вопросов для данного типа игры")
        
        if room["current_question"] >= len(game_questions):
            room["status"] = "completed"
            logger.info(f"🏁 Игра завершена в комнате {room_id}")
            return {"completed": True, "message": "Игра завершена!"}
        
        question = game_questions[room["current_question"]]
        
        logger.info(f"❓ Вопрос {room['current_question']+1}/{len(game_questions)} для комнаты {room_id}")
        
        return {
            "question_id": room["current_question"],
            "question": question["question"],
            "options": question["options"],
            "category": question["category"],
            "total_questions": len(game_questions),
            "current_number": room["current_question"] + 1
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка получения вопроса: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка получения вопроса")

@app.post("/api/submit-answer")
async def submit_answer(request: AnswerRequest):
    """✅ ИСПРАВЛЕНО: Отправить ответ на вопрос"""
    try:
        room = game_rooms.get(request.room_id)
        
        if not room:
            raise HTTPException(status_code=404, detail="Комната не найдена")
        
        # Сохраняем ответ
        answer_key = f"{request.question_id}_{request.player_name}"
        room["answers"][answer_key] = request.answer
        
        logger.info(f"💭 Ответ от {request.player_name} в комнате {request.room_id}: {request.answer}")
        
        # Проверяем, ответили ли оба игрока
        other_player = None
        for player in room["players"]:
            if player != request.player_name:
                other_player = player
                break
        
        both_answered = False
        if other_player:
            other_answer_key = f"{request.question_id}_{other_player}"
            both_answered = other_answer_key in room["answers"]
            
            if both_answered:
                room["current_question"] += 1
                logger.info(f"✅ Оба игрока ответили в комнате {request.room_id}, переход к вопросу {room['current_question']}")
                
                # Уведомляем через WebSocket о переходе к следующему вопросу
                await connection_manager.broadcast_to_room(request.room_id, {
                    "type": "next_question",
                    "current_question": room["current_question"]
                })
            else:
                # Уведомляем партнера, что один игрок ответил
                await connection_manager.broadcast_to_room(request.room_id, {
                    "type": "partner_answered",
                    "question_id": request.question_id,
                    "player": request.player_name
                })
        
        return {
            "success": True,
            "waiting_for_partner": not both_answered,
            "message": "Ответ сохранен!" if not both_answered else "Оба ответили! Следующий вопрос.",
            "current_question": room["current_question"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка отправки ответа: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка отправки ответа")

@app.get("/api/game-results/{room_id}")
async def get_game_results(room_id: str):
    """✅ ИСПРАВЛЕНО: Получить результаты игры"""
    try:
        room = game_rooms.get(room_id)
        
        if not room:
            raise HTTPException(status_code=404, detail="Комната не найдена")
        
        if room["status"] != "completed":
            return {"completed": False, "message": "Игра еще не завершена"}
        
        matches = 0
        total_questions = room["current_question"]
        results = []
        
        if len(room["players"]) >= 2:
            for q_id in range(total_questions):
                player1_answer = room["answers"].get(f"{q_id}_{room['players'][0]}")
                # ✅ ИСПРАВЛЕНО: Было  вместо [1]
                player2_answer = room["answers"].get(f"{q_id}_{room['players'][1]}")
                
                match = player1_answer == player2_answer
                if match:
                    matches += 1
                
                results.append({
                    "question_id": q_id,
                    "player1_answer": player1_answer,
                    "player2_answer": player2_answer,
                    "match": match
                })
        
        # Совместимость по гномам
        compatibility_percent = (matches / total_questions) * 100 if total_questions > 0 else 0
        gnome_analysis = get_gnome_compatibility_analysis(compatibility_percent)
        
        logger.info(f"🎯 Результаты игры в комнате {room_id}: {matches}/{total_questions} совпадений ({compatibility_percent:.1f}%)")
        
        return {
            "completed": True,
            "matches": matches,
            "total_questions": total_questions,
            "compatibility_percent": round(compatibility_percent, 1),
            "results": results,
            "gnome_analysis": gnome_analysis,
            "players": room["players"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка получения результатов: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка получения результатов")

# ============ WEBSOCKET ============
@app.websocket("/ws/game/{room_id}")
async def websocket_game_endpoint(websocket: WebSocket, room_id: str):
    """✅ WebSocket для реального времени"""
    await connection_manager.connect(room_id, websocket)
    
    try:
        while True:
            # Слушаем сообщения от клиента
            data = await websocket.receive_json()
            logger.info(f"📨 WebSocket сообщение в комнате {room_id}: {data}")
            
            # Обрабатываем разные типы событий
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif data.get("type") == "answer_submitted":
                # Уведомляем партнера об ответе
                await connection_manager.broadcast_to_room(room_id, {
                    "type": "partner_answered",
                    "question_id": data.get("question_id"),
                    "player": data.get("player")
                })
            elif data.get("type") == "join_notification":
                # Уведомляем о присоединении игрока
                await connection_manager.broadcast_to_room(room_id, {
                    "type": "player_joined",
                    "player": data.get("player")
                })
                
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket отключен от комнаты {room_id}")
        await connection_manager.disconnect(room_id, websocket)
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        await connection_manager.disconnect(room_id, websocket)

# ============ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ============
def get_gnome_compatibility_analysis(percent: float) -> dict:
    """Анализ совместимости от гномов"""
    if percent >= 80:
        return {
            "gnome": "Гном-Сердцевед",
            "title": "Идеальная пара! 💕",
            "message": "Гном-Сердцевед восхищен: 'Вы словно созданы друг для друга! Ваши души поют в унисон!'",
            "advice": "Продолжайте развивать ваши отношения - у вас прекрасная основа для счастливого будущего!",
            "color": "#ff69b4"
        }
    elif percent >= 60:
        return {
            "gnome": "Гном-Мудрец",
            "title": "Отличная совместимость! 💖",
            "message": "Гном-Мудрец кивает: 'Вы хорошо понимаете друг друга. Это крепкая основа для отношений!'",
            "advice": "Уделяйте больше времени общению - узнавайте друг друга еще лучше!",
            "color": "#4169e1"
        }
    elif percent >= 40:
        return {
            "gnome": "Гном-Дипломат",
            "title": "Есть потенциал! 💙",
            "message": "Гном-Дипломат размышляет: 'У вас есть различия, но это может сделать отношения интереснее!'",
            "advice": "Больше разговаривайте о ваших предпочтениях и интересах. Различия можно превратить в силу!",
            "color": "#32cd32"
        }
    else:
        return {
            "gnome": "Гном-Исследователь",
            "title": "Время для открытий! 💛",
            "message": "Гном-Исследователь улыбается: 'Вы - две уникальные личности! Впереди много интересных открытий!'",
            "advice": "Не расстраивайтесь! Изучайте друг друга, делитесь интересами. Любовь растет через понимание!",
            "color": "#ffa500"
        }

# ✅ НОВОЕ: Очистка кэша карт дня (запускать периодически)
async def cleanup_daily_cache():
    """Очистка старых карт дня"""
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    dates_to_delete = [date for date in daily_cards_cache.keys() if date != current_date]
    
    for old_date in dates_to_delete:
        del daily_cards_cache[old_date]
        logger.info(f"🗑️ Удалена карта дня для {old_date}")

# Очистка старых комнат
async def cleanup_old_rooms():
    """Удаление комнат старше 2 часов"""
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=2)
    
    rooms_to_delete = []
    for room_id, room in game_rooms.items():
        if isinstance(room["created_at"], datetime) and room["created_at"] < cutoff_time:
            rooms_to_delete.append(room_id)
    
    for room_id in rooms_to_delete:
        del game_rooms[room_id]
        logger.info(f"🗑️ Удалена старая комната {room_id}")

@app.get("/robots.txt")
async def robots_txt():
    return "User-agent: *\nDisallow: /"

# Для Render deployment
# В конце main.py измените запуск:
# В конце main.py
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"🚀 Запуск Gnome Horoscope API на порту {port}")
    
    # ✅ Настройки для WebSocket
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        ws_ping_interval=20,      # Пинг каждые 20 секунд
        ws_ping_timeout=20,       # Таймаут пинга 20 секунд
        access_log=True
    )


