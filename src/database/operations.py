"""
Модуль для операций с базой данных
Автор: Алексей Марышев
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from loguru import logger
import time

from .models import (
    GenerationRequest, 
    GeneratedInstruction, 
    UserFeedback,
    RefinementHistory,
    SystemStats,
    ProcessingStatus,
    RequestType
)


class DatabaseOperations:
    """Класс для работы с базой данных"""
    
    def __init__(self, db: Session):
        self.db = db
        
    # ============= CRUD операции для запросов =============
    
    def create_generation_request(
        self,
        input_prompt: str,
        request_type: RequestType = RequestType.TEXT_GENERATION,
        style: Optional[str] = None,
        materials: Optional[List[str]] = None,
        dimensions: Optional[Dict] = None,
        image_path: Optional[str] = None,
        image_thumbnail_path: Optional[str] = None,
        model_name: str = "gemma:2b",
        user_session_id: Optional[str] = None
    ) -> GenerationRequest:
        """Создание нового запроса на генерацию"""
        
        request = GenerationRequest(
            request_type=request_type,
            status=ProcessingStatus.PENDING,
            input_prompt=input_prompt,
            style=style,
            materials=materials,
            dimensions=dimensions,
            image_path=image_path,
            image_thumbnail_path=image_thumbnail_path,
            model_name=model_name,
            user_session_id=user_session_id
        )
        
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        
        logger.info(f"Создан новый запрос ID: {request.id}")
        return request
    
    def update_request_status(
        self, 
        request_id: int, 
        status: ProcessingStatus,
        instructions: Optional[Dict] = None,
        error_message: Optional[str] = None,
        processing_time: Optional[float] = None
    ) -> GenerationRequest:
        """Обновление статуса запроса"""
        
        request = self.db.query(GenerationRequest).filter(
            GenerationRequest.id == request_id
        ).first()
        
        if not request:
            raise ValueError(f"Запрос с ID {request_id} не найден")
        
        request.status = status
        request.updated_at = datetime.now()
        
        if instructions:
            request.generated_instructions = instructions
        if error_message:
            request.error_message = error_message
        if processing_time:
            request.processing_time = processing_time
            
        self.db.commit()
        self.db.refresh(request)
        
        logger.info(f"Обновлен статус запроса ID: {request_id} -> {status.value}")
        return request
    
    def get_request_by_id(self, request_id: int) -> Optional[GenerationRequest]:
        """Получение запроса по ID"""
        return self.db.query(GenerationRequest).filter(
            GenerationRequest.id == request_id
        ).first()
    
    def get_all_requests(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[ProcessingStatus] = None,
        user_session_id: Optional[str] = None
    ) -> List[GenerationRequest]:
        """Получение списка запросов с фильтрацией"""
        
        query = self.db.query(GenerationRequest)
        
        if status:
            query = query.filter(GenerationRequest.status == status)
        if user_session_id:
            query = query.filter(GenerationRequest.user_session_id == user_session_id)
            
        return query.order_by(desc(GenerationRequest.created_at))\
                   .limit(limit).offset(offset).all()
    
    def delete_request(self, request_id: int) -> bool:
        """Удаление запроса"""
        request = self.get_request_by_id(request_id)
        if request:
            self.db.delete(request)
            self.db.commit()
            logger.info(f"Удален запрос ID: {request_id}")
            return True
        return False
    
    # ============= Операции с инструкциями (совместимость) =============
    
    def create_instruction_from_request(
        self,
        request_id: int,
        name: str,
        tags: Optional[List[str]] = None
    ) -> GeneratedInstruction:
        """Создание записи инструкции из запроса (для совместимости)"""
        
        request = self.get_request_by_id(request_id)
        if not request or not request.generated_instructions:
            raise ValueError(f"Запрос {request_id} не содержит инструкций")
        
        instruction = GeneratedInstruction(
            name=name,
            input_prompt=request.input_prompt,
            instructions=request.generated_instructions,
            request_id=request_id,
            tags=tags
        )
        
        self.db.add(instruction)
        self.db.commit()
        self.db.refresh(instruction)
        
        return instruction
    
    def get_all_instructions(
        self,
        limit: int = 50,
        offset: int = 0,
        is_favorite: Optional[bool] = None
    ) -> List[GeneratedInstruction]:
        """Получение списка инструкций"""
        
        query = self.db.query(GeneratedInstruction)
        
        if is_favorite is not None:
            query = query.filter(GeneratedInstruction.is_favorite == is_favorite)
            
        return query.order_by(desc(GeneratedInstruction.created_at))\
                   .limit(limit).offset(offset).all()
    
    def toggle_favorite(self, instruction_id: int) -> GeneratedInstruction:
        """Переключение флага избранного"""
        
        instruction = self.db.query(GeneratedInstruction).filter(
            GeneratedInstruction.id == instruction_id
        ).first()
        
        if instruction:
            instruction.is_favorite = not instruction.is_favorite
            self.db.commit()
            self.db.refresh(instruction)
            
        return instruction
    
    # ============= Обратная связь =============
    
    def add_feedback(
        self,
        request_id: int,
        rating: Optional[int] = None,
        comment: Optional[str] = None,
        is_useful: Optional[bool] = None
    ) -> UserFeedback:
        """Добавление обратной связи"""
        
        feedback = UserFeedback(
            request_id=request_id,
            rating=rating,
            comment=comment,
            is_useful=is_useful
        )
        
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        
        return feedback
    
    def get_request_feedback(self, request_id: int) -> List[UserFeedback]:
        """Получение обратной связи для запроса"""
        
        return self.db.query(UserFeedback).filter(
            UserFeedback.request_id == request_id
        ).order_by(desc(UserFeedback.created_at)).all()
    
    # ============= История улучшений =============
    
    def add_refinement(
        self,
        request_id: int,
        feedback_provided: str,
        previous_instructions: Dict,
        refined_instructions: Dict
    ) -> RefinementHistory:
        """Добавление записи об улучшении"""
        
        # Получаем номер итерации
        last_refinement = self.db.query(RefinementHistory).filter(
            RefinementHistory.request_id == request_id
        ).order_by(desc(RefinementHistory.iteration_number)).first()
        
        iteration_number = 1 if not last_refinement else last_refinement.iteration_number + 1
        
        refinement = RefinementHistory(
            request_id=request_id,
            iteration_number=iteration_number,
            feedback_provided=feedback_provided,
            previous_instructions=previous_instructions,
            refined_instructions=refined_instructions
        )
        
        self.db.add(refinement)
        self.db.commit()
        self.db.refresh(refinement)
        
        return refinement
    
    def get_refinement_history(self, request_id: int) -> List[RefinementHistory]:
        """Получение истории улучшений"""
        
        return self.db.query(RefinementHistory).filter(
            RefinementHistory.request_id == request_id
        ).order_by(RefinementHistory.iteration_number).all()
    
    # ============= Статистика и аналитика =============
    
    def get_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Получение статистики системы за период"""
        
        start_date = datetime.now() - timedelta(days=days)
        
        # Общая статистика
        total_requests = self.db.query(func.count(GenerationRequest.id)).filter(
            GenerationRequest.created_at >= start_date
        ).scalar()
        
        # Статистика по статусам
        status_stats = self.db.query(
            GenerationRequest.status,
            func.count(GenerationRequest.id).label('count')
        ).filter(
            GenerationRequest.created_at >= start_date
        ).group_by(GenerationRequest.status).all()
        
        status_dict = {status.value: count for status, count in status_stats}
        
        # Среднее время обработки
        avg_processing_time = self.db.query(
            func.avg(GenerationRequest.processing_time)
        ).filter(
            and_(
                GenerationRequest.created_at >= start_date,
                GenerationRequest.processing_time.isnot(None)
            )
        ).scalar()
        
        # Статистика по типам запросов
        type_stats = self.db.query(
            GenerationRequest.request_type,
            func.count(GenerationRequest.id).label('count')
        ).filter(
            GenerationRequest.created_at >= start_date
        ).group_by(GenerationRequest.request_type).all()
        
        type_dict = {req_type.value: count for req_type, count in type_stats}
        
        # Средний рейтинг
        avg_rating = self.db.query(func.avg(UserFeedback.rating)).filter(
            UserFeedback.created_at >= start_date
        ).scalar()
        
        # Количество уникальных сессий
        unique_sessions = self.db.query(
            func.count(func.distinct(GenerationRequest.user_session_id))
        ).filter(
            and_(
                GenerationRequest.created_at >= start_date,
                GenerationRequest.user_session_id.isnot(None)
            )
        ).scalar()
        
        return {
            "period_days": days,
            "total_requests": total_requests or 0,
            "status_breakdown": status_dict,
            "average_processing_time": round(avg_processing_time, 2) if avg_processing_time else 0,
            "request_types": type_dict,
            "average_rating": round(avg_rating, 2) if avg_rating else 0,
            "unique_sessions": unique_sessions or 0,
            "successful_rate": round(
                (status_dict.get('completed', 0) / total_requests * 100) if total_requests > 0 else 0, 
                2
            )
        }
    
    def get_popular_styles(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение популярных стилей"""
        
        styles = self.db.query(
            GenerationRequest.style,
            func.count(GenerationRequest.id).label('count')
        ).filter(
            GenerationRequest.style.isnot(None)
        ).group_by(
            GenerationRequest.style
        ).order_by(
            desc('count')
        ).limit(limit).all()
        
        return [{"style": style, "count": count} for style, count in styles]
    
    def get_recent_activity(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Получение недавней активности"""
        
        start_time = datetime.now() - timedelta(hours=hours)
        
        requests = self.db.query(GenerationRequest).filter(
            GenerationRequest.created_at >= start_time
        ).order_by(desc(GenerationRequest.created_at)).limit(20).all()
        
        activity = []
        for req in requests:
            activity.append({
                "id": req.id,
                "type": req.request_type.value if req.request_type else "unknown",
                "status": req.status.value if req.status else "unknown",
                "prompt_preview": req.input_prompt[:100] + "..." if len(req.input_prompt) > 100 else req.input_prompt,
                "created_at": req.created_at.isoformat() if req.created_at else None,
                "processing_time": req.processing_time
            })
            
        return activity
    
    def search_requests(
        self,
        query: str,
        limit: int = 20
    ) -> List[GenerationRequest]:
        """Поиск запросов по тексту"""
        
        search_pattern = f"%{query}%"
        
        return self.db.query(GenerationRequest).filter(
            or_(
                GenerationRequest.input_prompt.ilike(search_pattern),
                GenerationRequest.style.ilike(search_pattern)
            )
        ).order_by(desc(GenerationRequest.created_at)).limit(limit).all()
    
    def update_system_stats(self):
        """Обновление ежедневной статистики системы"""
        
        today = datetime.now().date()
        
        # Проверяем, есть ли уже запись за сегодня
        stats = self.db.query(SystemStats).filter(
            func.date(SystemStats.date) == today
        ).first()
        
        if not stats:
            stats = SystemStats(date=datetime.combine(today, datetime.min.time()))
            self.db.add(stats)
        
        # Подсчитываем статистику за сегодня
        today_requests = self.db.query(GenerationRequest).filter(
            func.date(GenerationRequest.created_at) == today
        ).all()
        
        stats.total_requests = len(today_requests)
        stats.successful_requests = sum(1 for r in today_requests if r.status == ProcessingStatus.COMPLETED)
        stats.failed_requests = sum(1 for r in today_requests if r.status == ProcessingStatus.FAILED)
        
        # Среднее и общее время обработки
        processing_times = [r.processing_time for r in today_requests if r.processing_time]
        if processing_times:
            stats.average_processing_time = sum(processing_times) / len(processing_times)
            stats.total_processing_time = sum(processing_times)
        
        # Уникальные сессии
        unique_sessions = set(r.user_session_id for r in today_requests if r.user_session_id)
        stats.unique_sessions = len(unique_sessions)
        
        self.db.commit()
        
        logger.info(f"Обновлена статистика за {today}")


# Вспомогательные функции для быстрого доступа

def get_db_operations(db: Session) -> DatabaseOperations:
    """Получение экземпляра класса операций с БД"""
    return DatabaseOperations(db)


def process_generation_request(
    db: Session,
    input_prompt: str,
    style: Optional[str] = None,
    materials: Optional[List[str]] = None,
    **kwargs
) -> GenerationRequest:
    """Быстрое создание и обработка запроса"""
    
    ops = DatabaseOperations(db)
    
    # Создаем запрос
    request = ops.create_generation_request(
        input_prompt=input_prompt,
        style=style,
        materials=materials,
        **kwargs
    )
    
    # Обновляем статус на "в обработке"
    ops.update_request_status(request.id, ProcessingStatus.PROCESSING)
    
    start_time = time.time()
    
    try:
        # Здесь будет вызов генерации через AI
        # Пока заглушка
        instructions = {"status": "generated", "components": []}
        
        # Обновляем с результатом
        processing_time = time.time() - start_time
        ops.update_request_status(
            request.id,
            ProcessingStatus.COMPLETED,
            instructions=instructions,
            processing_time=processing_time
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        ops.update_request_status(
            request.id,
            ProcessingStatus.FAILED,
            error_message=str(e),
            processing_time=processing_time
        )
        raise
    
    return request