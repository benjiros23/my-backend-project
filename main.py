@app.get("/")
async def root():
    return {"message": "🧙‍♂️ Gnome Horoscope API is running!", "status": "ok"}

import os
import json
import random
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Gnome Horoscope API", version="1.0.0")

# CORS (разрешить всем доменам)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
            "POST /api/day-card - получить карту дня"
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
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
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

@app.post("/api/day-card")
async def get_day_card():
    """Получить карту дня"""
    try:
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
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")

# Для Render deployment
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Запуск Gnome Horoscope API на порту {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
