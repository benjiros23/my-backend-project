import os
import json
import random
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Gnome Horoscope API", version="1.0.0")

# CORS (разрешить всем доменам)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Модели данных
class FavoriteRequest(BaseModel):
    initData: str = ""
    type: str
    content: Any

# Гороскопы
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

# Карты дня
DAY_CARDS = [
    {"название": "Гном-авантюрист", "совет": "Сегодня время для смелых решений! Не бойся рискнуть - фортуна любит храбрых."},
    {"название": "Гном-повар", "совет": "День для заботы о своем теле и душе. Приготовь что-то вкусное или побалуй себя."},
    {"название": "Гном-садовник", "совет": "Время посадить семена будущих успехов. Небольшие действия сегодня принесут большие плоды."},
    {"название": "Гном-изобретатель", "совет": "Креативность зашкаливает сегодня! Придумай что-то новое или реши задачу нестандартным способом."},
    {"название": "Гном-музыкант", "совет": "Найди свой ритм дня. Включи любимую музыку и позволь мелодии вести тебя к успеху."},
    {"название": "Гном-философ", "совет": "Размышления принесут ясность. Уделите время анализу своих целей и желаний."},
    {"название": "Гном-путешественник", "совет": "Новые места и впечатления ждут! Даже короткая прогулка может стать приключением."},
    {"название": "Гном-мастер", "совет": "Руки помнят мудрость. Займитесь любимым делом или освойте новый навык."}
]

# Глобальное хранилище для избранного (в реальности - база данных)
user_favorites = {}

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Обработчик всех исключений"""
    logger.error(f"Unexpected error: {str(exc)}")
    return {"error": "Internal server error", "detail": "Произошла внутренняя ошибка сервера"}

@app.get("/")
async def root():
    """Корневой роут"""
    return {
        "message": "🧙‍♂️ Gnome Horoscope API is running!",
        "status": "ok",
        "version": "1.0.0",
        "endpoints": [
            "GET /health - проверка работоспособности",
            "GET /api/horoscope?sign=ЗНАК - получить гороскоп",
            "POST /api/day-card - получить карту дня",
            "GET /api/favorites - получить избранное",
            "POST /api/favorites - добавить в избранное"
        ]
    }

@app.get("/health")
async def health():
    """Проверка работоспособности"""
    return {
        "status": "ok", 
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "Gnome Horoscope API"
    }

@app.get("/api/horoscope")
async def get_horoscope(sign: str, date: str = None):
    """Получить гороскоп для знака зодиака"""
    try:
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        logger.info(f"Запрос гороскопа для {sign} на {date}")
        
        # Генерируем стабильный гороскоп на основе знака и даты
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
    """Получить карту дня"""
    try:
        logger.info("Запрос карты дня")
        
        # Возвращаем случайную карту
        card = random.choice(DAY_CARDS)
        
        return {
            "title": card["название"],
            "text": card["совет"],
            "reused": False,
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "source": "Gnome Horoscope API"
        }
    except Exception as e:
        logger.error(f"Ошибка при получении карты дня: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка при получении карты дня")

@app.get("/api/favorites")
async def get_favorites(initData: str = ""):
    """Получить избранное пользователя"""
    try:
        logger.info(f"Запрос избранного для пользователя")
        
        # Используем initData как ключ пользователя (в реальности - парсинг и валидация)
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
    """Добавить в избранное"""
    try:
        logger.info(f"Добавление в избранное: тип {request.type}")
        
        # Используем initData как ключ пользователя
        user_id = request.initData or "anonymous"
        
        if user_id not in user_favorites:
            user_favorites[user_id] = []
        
        # Создаем запись избранного
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

@app.get("/robots.txt")
async def robots_txt():
    """Файл robots.txt для поисковых роботов"""
    return "User-agent: *\nDisallow: /"

# Для Render deployment
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"🚀 Запуск Gnome Horoscope API на порту {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
