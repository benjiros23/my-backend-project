from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class HoroscopeResponse(BaseModel):
    sign: str
    date: str
    text: str
    cached: bool

class DayCardRequest(BaseModel):
    initData: str

class DayCardResponse(BaseModel):
    title: str
    text: str
    reused: bool
    date: str

class FavoriteRequest(BaseModel):
    initData: str
    type: str
    content: Dict[str, Any]

class FavoriteResponse(BaseModel):
    status: str
    message: str

class FavoritesResponse(BaseModel):
    favorites: list
