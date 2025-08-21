import os
import sqlite3
import json
import hashlib
import hmac
import time
import random
from datetime import datetime, timezone
from urllib.parse import unquote, parse_qs
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio

# Настройки
BOT_TOKEN = "8314608234:AAFQUNz63MECCtExqaKGqg02qm0GWv0Nbz4"  # Ваш токен
FRONTEND_URL = "https://gilded-blancmange-ecc392.netlify.app"  # Ваш фронтенд URL

app = FastAPI(title="Gnome Horoscope API", version="1.0.0")

# CORS для фронтенда (ОБНОВИТЕ этот блок)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://gilded-blancmange-ecc392.netlify.app",  # ✅ Ваш Netlify домен
        "https://gilded-blancmange-ecc392.netlify.app/", # ✅ С слешем на конце
        "http://localhost:3000",  # Для разработки
        "https://localhost:3000"  # На всякий случай
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Маппинг знаков зодиака
ZODIAC_MAP = {
    "Овен": "aries", "Телец": "taurus", "Близнецы": "gemini", "Рак": "cancer",
    "Лев": "leo", "Дева": "virgo", "Весы": "libra", "Скорпион": "scorpio",
    "Стрелец": "sagittarius", "Козерог": "capricorn", 
    "Водолей": "aquarius", "Рыбы": "pisces"
}

# Пул гороскопов (можно заменить на реальный API)
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

def get_db():
    """Инициализация базы данных"""
    # ИСПРАВЛЕНО: используем правильный путь к базе данных
    db_path = "database.db"  # База будет создана в текущей директории backend
    
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_cache (
            id INTEGER PRIMARY KEY,
            sign TEXT NOT NULL,
            date TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(sign, date)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS day_cards (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            card_title TEXT NOT NULL,
            card_text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(user_id, date)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            content_type TEXT NOT NULL,
            content TEXT NOT NULL,
            added_at TEXT NOT NULL
        )
    """)
    return conn

def verify_telegram_data(init_data: str) -> dict:
    """Проверка подлинности данных Telegram WebApp"""
    try:
        # Парсим init_data
        parsed_data = parse_qs(init_data)
        
        # Извлекаем hash
        received_hash = parsed_data.get('hash', [''])[0]
        if not received_hash:
            return None
            
        # Удаляем hash из данных для проверки
        data_to_check = []
        for key, value in parsed_data.items():
            if key != 'hash':
                data_to_check.append(f"{key}={value[0]}")
        
        # Сортируем и объединяем
        data_string = '\n'.join(sorted(data_to_check))
        
        # Создаем секретный ключ
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        
        # Вычисляем hash
        calculated_hash = hmac.new(secret_key, data_string.encode(), hashlib.sha256).hexdigest()
        
        # Проверяем hash
        if calculated_hash == received_hash:
            user_data = parsed_data.get('user', [''])[0]
            if user_data:
                user = json.loads(unquote(user_data))
                return user
                
    except Exception as e:
        print(f"Ошибка проверки Telegram данных: {e}")
        
    return None

def today_key():
    """Получить ключ для текущего дня"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

@app.get("/health")
async def health():
    """Проверка работоспособности API"""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/api/horoscope")
async def get_horoscope(sign: str, date: str = None):
    """Получить гороскоп для знака зодиака"""
    if date is None:
        date = today_key()
    
    # Проверяем знак зодиака
    if sign not in ZODIAC_MAP:
        raise HTTPException(status_code=400, detail="Неизвестный знак зодиака")
    
    conn = get_db()
    cur = conn.cursor()
    
    # Проверяем кеш
    cur.execute("SELECT text FROM daily_cache WHERE sign=? AND date=?", (sign, date))
    row = cur.fetchone()
    
    if row:
        conn.close()
        return {
            "sign": sign,
            "date": date,
            "text": row[0],
            "cached": True
        }
    
    # Генерируем новый гороскоп
    # Создаем сид на основе знака и даты для стабильности
    seed = hash(f"{sign}{date}") % len(HOROSCOPE_TEMPLATES)
    horoscope_text = HOROSCOPE_TEMPLATES[seed]
    
    # Сохраняем в кеш
    cur.execute(
        "INSERT OR REPLACE INTO daily_cache(sign, date, text, created_at) VALUES(?,?,?,?)",
        (sign, date, horoscope_text, datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    conn.close()
    
    return {
        "sign": sign,
        "date": date,
        "text": horoscope_text,
        "cached": False
    }

@app.post("/api/day-card")
async def get_day_card(request: Request):
    """Получить карту дня (один раз в сутки на пользователя)"""
    try:
        payload = await request.json()
        init_data = payload.get("initData")
        
        if not init_data:
            raise HTTPException(status_code=400, detail="initData отсутствует")
        
        # Проверяем данные Telegram
        user = verify_telegram_data(init_data)
        if not user:
            # В режиме разработки возвращаем тестовые данные
            user_id = 12345  # Тестовый ID
        else:
            user_id = user["id"]
        
        date = today_key()
        
        conn = get_db()
        cur = conn.cursor()
        
        # Проверяем, получал ли пользователь карту сегодня
        cur.execute("SELECT card_title, card_text FROM day_cards WHERE user_id=? AND date=?", (user_id, date))
        row = cur.fetchone()
        
        if row:
            conn.close()
            return {
                "title": row,
                "text": row,
                "reused": True,
                "date": date
            }
        
        # Выбираем случайную карту
        card = random.choice(DAY_CARDS)
        
        # Сохраняем карту для пользователя
        cur.execute(
            "INSERT INTO day_cards(user_id, date, card_title, card_text, created_at) VALUES(?,?,?,?,?)",
            (user_id, date, card["название"], card["совет"], datetime.now(timezone.utc).isoformat())
        )
        conn.commit()
        conn.close()
        
        return {
            "title": card["название"],
            "text": card["совет"],
            "reused": False,
            "date": date
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения карты дня: {str(e)}")

@app.post("/api/favorites")
async def add_favorite(request: Request):
    """Добавить в избранное"""
    try:
        payload = await request.json()
        init_data = payload.get("initData")
        content_type = payload.get("type")
        content = payload.get("content")
        
        if not all([init_data, content_type, content]):
            raise HTTPException(status_code=400, detail="Недостаточно данных")
        
        # Проверяем данные Telegram
        user = verify_telegram_data(init_data)
        user_id = user["id"] if user else 12345  # Тестовый ID
        
        conn = get_db()
        cur = conn.cursor()
        
        # Добавляем в избранное
        cur.execute(
            "INSERT INTO favorites(user_id, content_type, content, added_at) VALUES(?,?,?,?)",
            (user_id, content_type, json.dumps(content, ensure_ascii=False), datetime.now(timezone.utc).isoformat())
        )
        conn.commit()
        conn.close()
        
        return {"status": "added", "message": "Добавлено в избранное"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка добавления в избранное: {str(e)}")

@app.get("/api/favorites")
async def get_favorites(init_data: str):
    """Получить избранное пользователя"""
    try:
        if not init_data:
            raise HTTPException(status_code=400, detail="initData отсутствует")
        
        # Проверяем данные Telegram
        user = verify_telegram_data(init_data)
        user_id = user["id"] if user else 12345  # Тестовый ID
        
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("SELECT content_type, content, added_at FROM favorites WHERE user_id=? ORDER BY added_at DESC", (user_id,))
        rows = cur.fetchall()
        conn.close()
        
        favorites = []
        for row in rows:
            favorites.append({
                "type": row[0],
                "content": json.loads(row),
                "added_at": row
            })
        
        return {"favorites": favorites}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения избранного: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Запуск Gnome Horoscope API...")
    print(f"📡 CORS для: {FRONTEND_URL}")
    print(f"💾 База данных: database.db (в текущей папке)")
    uvicorn.run(app, host="0.0.0.0", port=8000)
# Для деплоя на Render
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

