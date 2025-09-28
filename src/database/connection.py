"""
Модуль для работы с базой данных (SQLite)
Автор: Алексей Марышев
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/architect.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Создание сессии для работы с БД"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Инициализация базы данных"""
    logger.info("Инициализация базы данных...")
    # Импортируем модели, чтобы они были зарегистрированы в Base
    from . import models
    Base.metadata.create_all(bind=engine)
    logger.info("База данных успешно инициализирована.")

if __name__ == "__main__":
    init_db()