import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pydantic import BaseModel

# Модели для игр
class GameRoom(BaseModel):
    room_id: str
    created_at: datetime
    players: List[str] = []
    game_type: str = ""
    current_question: int = 0
    answers: Dict[str, any] = {}
    status: str = "waiting"  # waiting, playing, completed

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

# Хранилище игровых комнат (в продакшене - Redis или БД)
game_rooms: Dict[str, GameRoom] = {}

# Загрузка вопросов (замени на реальный путь к файлу)
COUPLE_GAMES_DATA = {
    "fruit_game": [
        {
            "question": "Какой фрукт больше всего любит ваш партнер?",
            "options": ["🍎 Яблоко", "🍌 Банан", "🍊 Апельсин", "🍇 Виноград", "🥭 Манго", "🍓 Клубника"],
            "category": "taste"
        }
    ],
    "preference_test": [
        {
            "question": "Какой цвет больше всего нравится вашему партнеру?",
            "options": ["❤️ Красный", "💙 Синий", "💚 Зеленый", "💛 Желтый", "💜 Фиолетовый", "🖤 Черный"],
            "category": "colors"
        }
    ],
    "date_ideas": [
        {
            "question": "Идеальное свидание для вашего партнера:",
            "options": ["🎬 Кино", "🍽️ Ресторан", "🏞️ Прогулка в парке", "🏠 Дома с фильмом", "🎭 Театр", "🎪 Развлечения"],
            "category": "date_type"
        }
    ]
}

@app.post("/api/create-room")
async def create_room(request: dict):
    """Создать игровую комнату"""
    try:
        room_id = str(uuid.uuid4())[:8].upper()
        game_type = request.get('game_type', 'mixed')
        creator_name = request.get('creator_name', 'Player1')
        
        room = GameRoom(
            room_id=room_id,
            created_at=datetime.now(timezone.utc),
            players=[creator_name],
            game_type=game_type,
            status="waiting"
        )
        
        game_rooms[room_id] = room
        
        logger.info(f"Создана комната {room_id} для игры {game_type}")
        
        return {
            "success": True,
            "room_id": room_id,
            "message": f"Комната создана! Код: {room_id}"
        }
        
    except Exception as e:
        logger.error(f"Ошибка создания комнаты: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка создания комнаты")

@app.post("/api/join-room")
async def join_room(request: JoinRoomRequest):
    """Присоединиться к игровой комнате"""
    try:
        room = game_rooms.get(request.room_id)
        
        if not room:
            return {"success": False, "message": "Комната не найдена"}
            
        if len(room.players) >= 2:
            return {"success": False, "message": "Комната полна"}
            
        if request.player_name not in room.players:
            room.players.append(request.player_name)
            
        # Если два игрока - начинаем игру
        if len(room.players) == 2:
            room.status = "playing"
            
        return {
            "success": True,
            "message": "Присоединился к игре!",
            "players": room.players,
            "status": room.status
        }
        
    except Exception as e:
        logger.error(f"Ошибка присоединения к комнате: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка присоединения к комнате")

@app.get("/api/room-status/{room_id}")
async def get_room_status(room_id: str):
    """Получить статус комнаты"""
    try:
        room = game_rooms.get(room_id)
        
        if not room:
            raise HTTPException(status_code=404, detail="Комната не найдена")
            
        return {
            "room_id": room_id,
            "players": room.players,
            "status": room.status,
            "current_question": room.current_question,
            "player_count": len(room.players)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения статуса комнаты: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка получения статуса")

@app.get("/api/game-question/{room_id}")
async def get_game_question(room_id: str):
    """Получить текущий вопрос игры"""
    try:
        room = game_rooms.get(room_id)
        
        if not room:
            raise HTTPException(status_code=404, detail="Комната не найдена")
            
        # Получаем вопросы для типа игры
        game_questions = []
        if room.game_type == "mixed":
            # Смешанная игра - все типы вопросов
            for category in COUPLE_GAMES_DATA.values():
                game_questions.extend(category)
        else:
            game_questions = COUPLE_GAMES_DATA.get(room.game_type, [])
            
        if room.current_question >= len(game_questions):
            room.status = "completed"
            return {"completed": True, "message": "Игра завершена!"}
            
        question = game_questions[room.current_question]
        
        return {
            "question_id": room.current_question,
            "question": question["question"],
            "options": question["options"],
            "category": question["category"],
            "total_questions": len(game_questions)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения вопроса: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка получения вопроса")

@app.post("/api/submit-answer")
async def submit_answer(request: AnswerRequest):
    """Отправить ответ на вопрос"""
    try:
        room = game_rooms.get(request.room_id)
        
        if not room:
            raise HTTPException(status_code=404, detail="Комната не найдена")
            
        # Сохраняем ответ
        answer_key = f"{request.question_id}_{request.player_name}"
        room.answers[answer_key] = request.answer
        
        # Проверяем, ответили ли оба игрока
        other_player = [p for p in room.players if p != request.player_name][0]
        other_answer_key = f"{request.question_id}_{other_player}"
        
        both_answered = other_answer_key in room.answers
        
        if both_answered:
            # Переходим к следующему вопросу
            room.current_question += 1
            
        return {
            "success": True,
            "waiting_for_partner": not both_answered,
            "message": "Ответ сохранен!" if not both_answered else "Оба ответили! Следующий вопрос."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка отправки ответа: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка отправки ответа")

@app.get("/api/game-results/{room_id}")
async def get_game_results(room_id: str):
    """Получить результаты игры"""
    try:
        room = game_rooms.get(room_id)
        
        if not room:
            raise HTTPException(status_code=404, detail="Комната не найдена")
            
        if room.status != "completed":
            return {"completed": False, "message": "Игра еще не завершена"}
            
        # Анализируем ответы
        matches = 0
        total_questions = room.current_question
        results = []
        
        for q_id in range(total_questions):
            player1_answer = room.answers.get(f"{q_id}_{room.players[0]}")
            player2_answer = room.answers.get(f"{q_id}_{room.players[1]}")
            
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
        
        return {
            "completed": True,
            "matches": matches,
            "total_questions": total_questions,
            "compatibility_percent": compatibility_percent,
            "results": results,
            "gnome_analysis": gnome_analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения результатов: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка получения результатов")

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

# Очистка старых комнат (можно запускать периодически)
async def cleanup_old_rooms():
    """Удаление комнат старше 2 часов"""
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=2)
    
    rooms_to_delete = [
        room_id for room_id, room in game_rooms.items() 
        if room.created_at < cutoff_time
    ]
    
    for room_id in rooms_to_delete:
        del game_rooms[room_id]
        logger.info(f"Удалена старая комната {room_id}")
