"""
Модели SQLAlchemy для базы данных
Автор: Алексей Марышев
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, Float, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .connection import Base
import enum


class ProcessingStatus(enum.Enum):
    """Статусы обработки запросов"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    

class RequestType(enum.Enum):
    """Типы запросов"""
    TEXT_GENERATION = "text_generation"
    IMAGE_ANALYSIS = "image_analysis"
    REFINEMENT = "refinement"


class GenerationRequest(Base):
    """Модель для запросов на генерацию"""
    __tablename__ = "generation_requests"

    id = Column(Integer, primary_key=True, index=True)
    request_type = Column(Enum(RequestType), default=RequestType.TEXT_GENERATION)
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING, index=True)
    
    # Входные данные
    input_prompt = Column(Text, nullable=False)
    style = Column(String(100))
    materials = Column(JSON)  # Список материалов
    dimensions = Column(JSON)  # Размеры объекта
    image_path = Column(String(500))  # Путь к загруженному изображению
    
    # Параметры генерации
    model_name = Column(String(100), default="gemma:2b")
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=2048)
    
    # Результаты
    generated_instructions = Column(JSON)  # Сгенерированный JSON с инструкциями
    error_message = Column(Text)  # Сообщение об ошибке, если status = FAILED
    processing_time = Column(Float)  # Время обработки в секундах
    
    # Метаданные
    user_session_id = Column(String(100))  # ID сессии пользователя
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    feedback_items = relationship("UserFeedback", back_populates="request", cascade="all, delete-orphan")
    refinements = relationship("RefinementHistory", back_populates="request", cascade="all, delete-orphan")


class GeneratedInstruction(Base):
    """Модель для сгенерированных инструкций (совместимость с текущим кодом)"""
    __tablename__ = "generated_instructions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    input_prompt = Column(Text) # Исходный текстовый запрос
    instructions = Column(JSON) # Сгенерированный JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Новые поля для расширенной функциональности
    request_id = Column(Integer, ForeignKey("generation_requests.id"))
    is_favorite = Column(Boolean, default=False)
    tags = Column(JSON)  # Список тегов для категоризации
    

class UserFeedback(Base):
    """Модель для обратной связи пользователей"""
    __tablename__ = "user_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("generation_requests.id"), nullable=False)
    rating = Column(Integer)  # Оценка от 1 до 5
    comment = Column(Text)
    is_useful = Column(Boolean)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    request = relationship("GenerationRequest", back_populates="feedback_items")
    

class RefinementHistory(Base):
    """История улучшений инструкций"""
    __tablename__ = "refinement_history"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("generation_requests.id"), nullable=False)
    iteration_number = Column(Integer, default=1)
    feedback_provided = Column(Text)  # Обратная связь для улучшения
    previous_instructions = Column(JSON)  # Предыдущая версия инструкций
    refined_instructions = Column(JSON)  # Улучшенная версия
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    request = relationship("GenerationRequest", back_populates="refinements")
    

class SystemStats(Base):
    """Статистика использования системы"""
    __tablename__ = "system_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    total_requests = Column(Integer, default=0)
    successful_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    average_processing_time = Column(Float)
    total_processing_time = Column(Float)
    unique_sessions = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

