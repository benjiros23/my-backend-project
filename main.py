import os
import json
import random
import logging
import uuid
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

# ============ НАСТРОЙКА ЛОГИРОВАНИЯ ============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============ СОЗДАНИЕ ПРИЛОЖЕНИЯ ============
app = FastAPI(
    title="Gnome Horoscope API",
    version="2.0.0",
    description="🧙‍♂️ API для мини-приложения Гномий Гороскоп"
)

# ============ CORS НАСТРОЙКА ============
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8080",
        "https://gilded-blancmange-ecc392.netlify.app",
        "https://*.netlify.app",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ ГЛОБАЛЬНЫЙ ОБРАБОТЧИК ОШИБОК ============
@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    logger.error(f"❌ 500 Error на {request.url}: {str(exc)}")
    logger.error(f"📋 Трассировка: {traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутренняя ошибка сервера", "error": str(exc)}
    )

# ============ МОДЕЛИ ДАННЫХ ============
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

# ============ ДАННЫЕ ПРИЛОЖЕНИЯ ============
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

# ============ ЗАГРУЗКА ВОПРОСОВ ============
COUPLE_GAMES_DATA = {}

def load_questions_from_file():
    """Загружаем вопросы из JSON файла"""
    global COUPLE_GAMES_DATA
    
    possible_paths = [
        "questions.json",
        "./questions.json",
        "modules/couple-games/questions.json",
        "./modules/couple-games/questions.json"
    ]
    
    for file_path in possible_paths:
        try:
            if Path(file_path).exists():
                logger.info(f"📁 Найден файл вопросов: {file_path}")
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    COUPLE_GAMES_DATA = json.load(f)
                
                total_questions = sum(len(category) for category in COUPLE_GAMES_DATA.values())
                logger.info(f"✅ Загружено {total_questions} вопросов из {len(COUPLE_GAMES_DATA)} категорий")
                
                for category, questions in COUPLE_GAMES_DATA.items():
                    logger.info(f"  - {category}: {len(questions)} вопросов")
                
                return True
                
        except Exception as e:
            logger.warning(f"❌ Ошибка загрузки {file_path}: {e}")
            continue
    
    # Fallback данные если файл не найден
    logger.warning("⚠️ JSON файл не найден, используем fallback данные")
    COUPLE_GAMES_DATA = {
        "fruit_game": [
            {"question": "Какой фрукт больше всего любит ваш партнер?", "options": ["🍎 Яблоко", "🍌 Банан", "🍊 Апельсин", "🍇 Виноград", "🥭 Манго", "🍓 Клубника"], "category": "taste"},
            {"question": "Какой экзотический фрукт хотел бы попробовать ваш партнер?", "options": ["🥥 Кокос", "🥝 Киви", "🍍 Ананас", "🥭 Манго", "🍈 Дыня", "🍑 Черешня"], "category": "taste"},
            {"question": "Какую ягоду предпочитает ваш партнер?", "options": ["🍓 Клубника", "🫐 Черника", "🍇 Виноград", "🍒 Вишня", "🥝 Крыжовник", "🍑 Малина"], "category": "taste"}
        ],
        "preference_test": [
            {"question": "Какой цвет больше всего нравится вашему партнеру?", "options": ["❤️ Красный", "💙 Синий", "💚 Зеленый", "💛 Желтый", "💜 Фиолетовый", "🖤 Черный"], "category": "colors"},
            {"question": "Какую музыку предпочитает ваш партнер?", "options": ["🎸 Рок", "🎵 Поп", "🎹 Классика", "🎺 Джаз", "🎤 Рэп", "🎻 Инди"], "category": "music"},
            {"question": "Какое время года любит ваш партнер?", "options": ["🌸 Весна", "☀️ Лето", "🍂 Осень", "❄️ Зима"], "category": "seasons"}
        ],
        "date_ideas": [
            {"question": "Идеальное свидание для вашего партнера:", "options": ["🎬 Кино", "🍽️ Ресторан", "🏞️ Прогулка в парке", "🏠 Дома с фильмом", "🎭 Театр", "🎪 Развлечения"], "category": "date_type"},
            {"question": "Какое время для свидания предпочитает партнер?", "options": ["🌅 Утро", "☀️ День", "🌆 Вечер", "🌙 Ночь"], "category": "date_time"}
        ]
    }
    return False

# Загружаем вопросы при запуске
load_questions_from_file()

# ============ ХРАНИЛИЩА ДАННЫХ ============
user_favorites = {}
game_rooms: Dict[str, Dict[str, Any]] = {}
daily_cards_cache = {}

# ============ ОСНОВНЫЕ МАРШРУТЫ ============
@app.get("/")
async def root():
    total_questions = sum(len(category) for category in COUPLE_GAMES_DATA.values())
    return {
        "message": "🧙‍♂️ Gnome Horoscope API is running!",
        "status": "ok",
        "version": "2.0.0",
        "loaded_questions": total_questions,
        "categories": list(COUPLE_GAMES_DATA.keys()),
        "endpoints": [
            "GET /health",
            "GET /api/questions",
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
    """Детерминированная карта дня"""
    try:
        logger.info("Запрос карты дня")
        
        current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        if current_date in daily_cards_cache:
            card_data = daily_cards_cache[current_date]
            logger.info(f"📦 Карта дня из кэша для {current_date}")
        else:
            date_seed = hash(current_date) % len(DAY_CARDS)
            selected_card = DAY_CARDS[date_seed]
            
            card_data = {
                "title": selected_card["название"],
                "text": selected_card["совет"],
                "reused": False,
                "date": current_date,
                "source": "Gnome Horoscope API"
            }
            
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

@app.get("/api/questions")
async def get_all_questions():
    """Отдаем все загруженные вопросы"""
    return {
        "success": True,
        "questions": COUPLE_GAMES_DATA,
        "total_questions": sum(len(category) for category in COUPLE_GAMES_DATA.values()),
        "categories": list(COUPLE_GAMES_DATA.keys())
    }

# ============ МАРШРУТЫ ДЛЯ ИГР ============
# ============ НОВАЯ ЛОГИКА ИГР ============
@app.post("/api/create-room")
async def create_room(request: CreateRoomRequest):
    """Создать игровую комнату с новой логикой"""
    try:
        room_id = str(uuid.uuid4())[:8].upper()
        
        room = {
            "room_id": room_id,
            "created_at": datetime.now(timezone.utc),
            "players": [request.creator_name],
            "game_type": request.game_type,
            "current_question": 0,
            "current_phase": 1,  # 1 = Player1 отвечает, Player2 угадывает
            "current_answerer": request.creator_name,  # Кто сейчас отвечает за себя
            "answers": {},  # Ответы игроков о себе
            "guesses": {},  # Догадки игроков о партнерах
            "status": "waiting"
        }
        
        game_rooms[room_id] = room
        logger.info(f"✅ Создана комната {room_id} для игры {request.game_type}")
        
        return {
            "success": True,
            "room_id": room_id,
            "message": f"Комната создана! Код: {room_id}"
        }
    except Exception as e:
        logger.error(f"❌ Ошибка создания комнаты: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка создания комнаты")

@app.get("/api/game-question/{room_id}")
async def get_game_question(room_id: str):
    """Получить текущий вопрос с правильной логикой"""
    try:
        room = game_rooms.get(room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Комната не найдена")
        
        # Получаем вопросы
        game_questions = []
        if room["game_type"] == "mixed":
            for category in COUPLE_GAMES_DATA.values():
                game_questions.extend(category)
        else:
            game_questions = COUPLE_GAMES_DATA.get(room["game_type"], [])
        
        # Проверяем завершение игры
        total_rounds = len(game_questions) * 2  # Каждый вопрос в двух фазах
        
        if room["current_question"] >= total_rounds:
            room["status"] = "completed"
            logger.info(f"🏁 Игра завершена! Всего раундов: {room['current_question']}")
            return {"completed": True, "message": "Игра завершена!"}
        
        # Определяем текущий вопрос и фазу
        question_index = (room["current_question"] // 2) % len(game_questions)
        phase = room["current_phase"]
        current_answerer = room["current_answerer"]
        players = room["players"]
        
        question_data = game_questions[question_index]
        
        # ✅ НОВАЯ ЛОГИКА: Разные формулировки для разных ролей
        if current_answerer == players[0]:  # Player1 отвечает
            if phase == 1:
                # Player1 отвечает за себя
                question_text = question_data["question"].replace("партнер", "вы").replace("ваш партнер", "вы")
                instruction = f"({players[0]} отвечает за себя)"
                role = "answering"
            else:
                # Player1 угадывает ответ Player2
                question_text = question_data["question"].replace("партнер", players[1])
                instruction = f"({players[0]} угадывает предпочтения {players[1]})"
                role = "guessing"
        else:  # Player2
            if phase == 1:
                # Player2 угадывает ответ Player1
                question_text = question_data["question"].replace("партнер", players[0])
                instruction = f"({players[1]} угадывает предпочтения {players[0]})"
                role = "guessing"
            else:
                # Player2 отвечает за себя
                question_text = question_data["question"].replace("партнер", "вы").replace("ваш партнер", "вы")
                instruction = f"({players[1]} отвечает за себя)"
                role = "answering"
        
        logger.info(f"❓ Вопрос {room['current_question']+1}/{total_rounds}, фаза {phase}, отвечает: {current_answerer}")
        
        return {
            "question_id": room["current_question"],
            "question": question_text,
            "instruction": instruction,
            "options": question_data["options"],
            "category": question_data["category"],
            "total_questions": total_rounds,
            "current_number": room["current_question"] + 1,
            "phase": phase,
            "current_answerer": current_answerer,
            "role": role,  # "answering" или "guessing"
            "source": "JSON file"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка get_game_question: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/submit-answer")
async def submit_answer(request: AnswerRequest):
    """Отправить ответ с новой логикой"""
    try:
        room = game_rooms.get(request.room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Комната не найдена")
        
        players = room["players"]
        current_answerer = room["current_answerer"]
        phase = room["current_phase"]
        
        # Определяем, что это - ответ за себя или догадка о партнере
        if request.player_name == current_answerer:
            if phase == 1 and current_answerer == players[0]:
                # Player1 отвечает за себя
                room["answers"][f"{request.question_id}_{players[0]}"] = request.answer
                logger.info(f"💭 {players[0]} ответил за себя: {request.answer}")
            elif phase == 2 and current_answerer == players[1]:
                # Player2 отвечает за себя
                room["answers"][f"{request.question_id}_{players[1]}"] = request.answer
                logger.info(f"💭 {players[1]} ответил за себя: {request.answer}")
            else:
                # Игрок угадывает
                target_player = players[1] if request.player_name == players[0] else players[0]
                room["guesses"][f"{request.question_id}_{request.player_name}_about_{target_player}"] = request.answer
                logger.info(f"🔮 {request.player_name} угадывает про {target_player}: {request.answer}")
        else:
            # Второй игрок (не current_answerer) всегда угадывает
            target_player = current_answerer
            room["guesses"][f"{request.question_id}_{request.player_name}_about_{target_player}"] = request.answer
            logger.info(f"🔮 {request.player_name} угадывает про {target_player}: {request.answer}")
        
        # Проверяем, ответили ли оба игрока в текущем раунде
        round_complete = False
        if phase == 1:
            # Проверяем, есть ли ответ от отвечающего и догадка от угадывающего
            answer_key = f"{request.question_id}_{current_answerer}"
            guesser = players[1] if current_answerer == players[0] else players[0]
            guess_key = f"{request.question_id}_{guesser}_about_{current_answerer}"
            
            round_complete = answer_key in room["answers"] and guess_key in room["guesses"]
        else:
            # Аналогично для phase 2
            answer_key = f"{request.question_id}_{current_answerer}"
            guesser = players[0] if current_answerer == players[1] else players[1]
            guess_key = f"{request.question_id}_{guesser}_about_{current_answerer}"
            
            round_complete = answer_key in room["answers"] and guess_key in room["guesses"]
        
        if round_complete:
            # Переходим к следующей фазе или следующему вопросу
            if phase == 1:
                # Переходим к фазе 2 (меняем роли)
                room["current_phase"] = 2
                room["current_answerer"] = players[1] if current_answerer == players[0] else players[0]
            else:
                # Переходим к следующему вопросу
                room["current_question"] += 1
                room["current_phase"] = 1
                room["current_answerer"] = players[0]  # Начинаем с первого игрока
            
            logger.info(f"✅ Раунд завершен! Переход к следующему этапу")
        
        return {
            "success": True,
            "waiting_for_partner": not round_complete,
            "message": "Ответ сохранен!" if not round_complete else "Оба ответили! Следующий этап."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка отправки ответа: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка отправки ответа")

@app.get("/api/game-results/{room_id}")
async def get_game_results(room_id: str):
    """Получить результаты игры с новой логикой подсчета"""
    try:
        logger.info(f"🏆 Запрос результатов для комнаты: {room_id}")
        
        room = game_rooms.get(room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Комната не найдена")
        
        if room["status"] != "completed":
            return {"completed": False, "message": "Игра еще не завершена"}
        
        players = room["players"]
        answers = room.get("answers", {})
        guesses = room.get("guesses", {})
        
        # Подсчитываем правильные догадки
        correct_guesses = 0
        total_guesses = 0
        results = []
        
        # Получаем количество вопросов
        game_questions = []
        if room["game_type"] == "mixed":
            for category in COUPLE_GAMES_DATA.values():
                game_questions.extend(category)
        else:
            game_questions = COUPLE_GAMES_DATA.get(room["game_type"], [])
        
        for q_id in range(len(game_questions)):
            # Player1 отвечает, Player2 угадывает
            p1_answer = answers.get(f"{q_id}_{players[0]}")
            p2_guess_about_p1 = guesses.get(f"{q_id}_{players[1]}_about_{players[0]}")
            
            # Player2 отвечает, Player1 угадывает  
            p2_answer = answers.get(f"{q_id}_{players[1]}")
            p1_guess_about_p2 = guesses.get(f"{q_id}_{players[0]}_about_{players[1]}")
            
            # Проверяем правильность догадок
            if p1_answer and p2_guess_about_p1:
                total_guesses += 1
                if p1_answer == p2_guess_about_p1:
                    correct_guesses += 1
                    
            if p2_answer and p1_guess_about_p2:
                total_guesses += 1
                if p2_answer == p1_guess_about_p2:
                    correct_guesses += 1
            
            results.append({
                "question_id": q_id,
                "question": game_questions[q_id]["question"],
                "player1_answer": p1_answer,
                "player2_guess_about_player1": p2_guess_about_p1,
                "player2_answer": p2_answer,
                "player1_guess_about_player2": p1_guess_about_p2,
                "p2_guessed_p1_correctly": p1_answer == p2_guess_about_p1 if p1_answer and p2_guess_about_p1 else False,
                "p1_guessed_p2_correctly": p2_answer == p1_guess_about_p2 if p2_answer and p1_guess_about_p2 else False
            })
        
        # Вычисляем процент правильных догадок
        compatibility_percent = (correct_guesses / total_guesses * 100) if total_guesses > 0 else 0
        
        # Анализ от гномов
        gnome_analysis = get_gnome_compatibility_analysis(compatibility_percent)
        
        logger.info(f"✅ Результаты: {correct_guesses}/{total_guesses} правильных догадок ({compatibility_percent:.1f}%)")
        
        return {
            "completed": True,
            "correct_guesses": correct_guesses,
            "total_guesses": total_guesses,
            "compatibility_percent": compatibility_percent,
            "results": results,
            "gnome_analysis": gnome_analysis,
            "explanation": f"Из {total_guesses} попыток угадать предпочтения партнера правильными оказались {correct_guesses}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
        # ============ РЕТРОГРАДНЫЙ МЕРКУРИЙ ============
MERCURY_RETROGRADE_2025 = [
    {
        "phase": "Mercury Retrograde #1",
        "pre_shadow_start": "2025-02-28",
        "retrograde_start": "2025-03-14", 
        "retrograde_end": "2025-04-07",
        "post_shadow_end": "2025-04-26",
        "signs": ["Aries", "Pisces"],
        "influences": {
            "communication": "Будьте осторожны в переписке, перечитывайте сообщения дважды",
            "travel": "Планы поездок могут измениться, проверяйте билеты",
            "technology": "Делайте резервные копии данных, технические сбои возможны",
            "relationships": "Старые знакомые могут неожиданно выйти на связь"
        }
    },
    {
        "phase": "Mercury Retrograde #2", 
        "pre_shadow_start": "2025-06-29",
        "retrograde_start": "2025-07-17",
        "retrograde_end": "2025-08-11", 
        "post_shadow_end": "2025-08-25",
        "signs": ["Leo"],
        "influences": {
            "creativity": "Пересмотрите творческие проекты, вдохновение найдет новые пути",
            "self_expression": "Осторожнее с публичными заявлениями и самопрезентацией", 
            "romance": "В отношениях возможны недопонимания из-за гордости",
            "performance": "Выступления и презентации требуют особой подготовки"
        }
    },
    {
        "phase": "Mercury Retrograde #3",
        "pre_shadow_start": "2025-10-21", 
        "retrograde_start": "2025-11-09",
        "retrograde_end": "2025-11-29",
        "post_shadow_end": "2025-12-16", 
        "signs": ["Sagittarius"],
        "influences": {
            "learning": "Пересмотрите планы обучения, возможны задержки в учебе",
            "travel": "Дальние поездки требуют особого внимания к деталям",
            "beliefs": "Время переосмыслить свои взгляды и философию жизни", 
            "legal": "Юридические вопросы лучше отложить на более поздний срок"
        }
    }
]

def get_mercury_status(date_str: str = None):
    """Проверяет статус Меркурия на указанную дату"""
    from datetime import datetime
    
    if date_str is None:
        check_date = datetime.now().strftime("%Y-%m-%d")
    else:
        check_date = date_str
    
    for period in MERCURY_RETROGRADE_2025:
        # Проверяем активную фазу ретрограда
        if period["retrograde_start"] <= check_date <= period["retrograde_end"]:
            return {
                "status": "retrograde",
                "phase": period["phase"],
                "signs": period["signs"],
                "influences": period["influences"],
                "start_date": period["retrograde_start"],
                "end_date": period["retrograde_end"],
                "message": f"🪐 Меркурий в ретрограде в знаке {', '.join(period['signs'])}! Будьте осторожны с коммуникациями."
            }
        
        # Проверяем теневую фазу (до ретрограда)
        elif period["pre_shadow_start"] <= check_date < period["retrograde_start"]:
            return {
                "status": "pre_shadow", 
                "phase": period["phase"],
                "signs": period["signs"],
                "influences": period["influences"],
                "start_date": period["retrograde_start"],
                "end_date": period["retrograde_end"],
                "message": f"⚡ Приближается ретроградный Меркурий! Начните подготовку с {period['retrograde_start']}."
            }
        
        # Проверяем теневую фазу (после ретрограда)
        elif period["retrograde_end"] < check_date <= period["post_shadow_end"]:
            return {
                "status": "post_shadow",
                "phase": period["phase"], 
                "signs": period["signs"],
                "influences": period["influences"],
                "start_date": period["retrograde_start"],
                "end_date": period["retrograde_end"],
                "message": f"🌅 Меркурий выходит из ретрограда. Эффекты ослабевают до {period['post_shadow_end']}."
            }
    
    return {
        "status": "direct",
        "message": "✨ Меркурий движется прямо. Благоприятное время для коммуникаций и новых начинаний!",
        "influences": {
            "communication": "Отличное время для важных разговоров и переговоров",
            "technology": "Техника работает стабильно, можно покупать новые устройства", 
            "travel": "Путешествия проходят гладко, можно планировать поездки",
            "contracts": "Благоприятное время для подписания договоров"
        }
    }

def get_weekly_mercury_forecast():
    """Получить прогноз влияния Меркурия на неделю"""
    from datetime import datetime, timedelta
    
    today = datetime.now()
    forecast = []
    
    for i in range(7):
        date = (today + timedelta(days=i)).strftime("%Y-%m-%d")
        status = get_mercury_status(date)
        forecast.append({
            "date": date,
            "day_name": (today + timedelta(days=i)).strftime("%A"), 
            "mercury_status": status["status"],
            "message": status["message"],
            "key_influences": list(status["influences"].keys())[:2] if "influences" in status else []
        })
    
    return {
        "week_forecast": forecast,
        "summary": "Еженедельный прогноз влияния Меркурия на различные сферы жизни"
    }

# API endpoint для Меркурия
@app.get("/api/mercury-status")
async def get_mercury_retrograde_status(date: str = None):
    """Получить текущий статус ретроградного Меркурия"""
    try:
        logger.info(f"Запрос статуса Меркурия на дату: {date}")
        
        mercury_info = get_mercury_status(date)
        weekly_forecast = get_weekly_mercury_forecast()
        
        return {
            "success": True,
            "current_status": mercury_info,
            "weekly_forecast": weekly_forecast,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения статуса Меркурия: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка получения статуса Меркурия")


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

@app.get("/robots.txt")
async def robots_txt():
    return "User-agent: *\nDisallow: /"

# ============ ЗАПУСК ПРИЛОЖЕНИЯ ============
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"🚀 Запуск Gnome Horoscope API на порту {port}")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port
    )
