"""
Скрипт для инициализации и миграции базы данных
Автор: Алексей Марышев
"""

import os
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from src.database.connection import engine, init_db
from src.database.models import Base
from loguru import logger


def create_database(force_recreate=False):
    """Создание всех таблиц в базе данных
    
    Args:
        force_recreate: Если True, удаляет существующую БД и создает новую
    """
    logger.info("Инициализация базы данных...")
    
    db_path = ROOT_DIR / "data" / "architect.db"
    
    # Создаем директорию если её нет
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    if db_path.exists():
        logger.info(f"База данных найдена: {db_path}")
        
        if force_recreate:
            response = input("\n⚠️  ВНИМАНИЕ: Вы хотите УДАЛИТЬ существующую БД и создать новую? Все данные будут потеряны! (yes/no): ")
            if response.lower() == 'yes':
                os.remove(db_path)
                logger.warning("Старая база данных удалена")
            else:
                logger.info("Операция отменена")
                return
        else:
            logger.info("Используем существующую базу данных")
            
            # Проверяем, есть ли все необходимые таблицы
            from sqlalchemy import inspect
            inspector = inspect(engine)
            existing_tables = inspector.get_table_names()
            
            logger.info(f"Существующие таблицы: {', '.join(existing_tables) if existing_tables else 'нет таблиц'}")
    else:
        logger.info("База данных не найдена, создаем новую...")
    
    # Создаем все таблицы (CREATE TABLE IF NOT EXISTS)
    Base.metadata.create_all(bind=engine)
    logger.success("База данных успешно инициализирована!")
    
    # Показываем созданные таблицы
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    logger.info(f"Созданные таблицы: {', '.join(tables)}")
    
    # Показываем структуру каждой таблицы
    for table_name in tables:
        columns = inspector.get_columns(table_name)
        logger.info(f"\nТаблица '{table_name}':")
        for col in columns:
            logger.info(f"  - {col['name']}: {col['type']}")


def show_database_stats():
    """Показать статистику БД"""
    from src.database.connection import get_db
    from src.database.operations import DatabaseOperations
    from src.database.models import GenerationRequest, GeneratedInstruction, ProcessingStatus
    
    logger.info("\n" + "="*60)
    logger.info("📊 Статистика базы данных:")
    
    db = next(get_db())
    try:
        # Подсчитываем записи
        total_requests = db.query(GenerationRequest).count()
        total_instructions = db.query(GeneratedInstruction).count()
        completed_requests = db.query(GenerationRequest).filter(
            GenerationRequest.status == ProcessingStatus.COMPLETED
        ).count()
        
        logger.info(f"  • Всего запросов: {total_requests}")
        logger.info(f"  • Завершенных запросов: {completed_requests}")
        logger.info(f"  • Сохраненных инструкций: {total_instructions}")
        
        # Показываем последние запросы
        if total_requests > 0:
            recent_requests = db.query(GenerationRequest).order_by(
                GenerationRequest.created_at.desc()
            ).limit(3).all()
            
            logger.info("\n  🕒 Последние запросы:")
            for req in recent_requests:
                logger.info(f"    - {req.input_prompt[:50]}... (ID: {req.id})")
    finally:
        db.close()
    
    logger.info("=" * 60)


def test_database():
    """Тестирование работы с базой данных (добавление тестовых данных)"""
    from src.database.connection import get_db
    from src.database.operations import DatabaseOperations
    from src.database.models import ProcessingStatus, RequestType
    
    logger.info("\nТестирование операций с БД...")
    
    # Получаем сессию
    db = next(get_db())
    db_ops = DatabaseOperations(db)
    
    try:
        # Создаем тестовый запрос
        test_request = db_ops.create_generation_request(
            input_prompt="Тестовый запрос: современный дом с плоской крышей",
            request_type=RequestType.TEXT_GENERATION,
            style="Минимализм",
            materials=["бетон", "стекло"],
            user_session_id="test_session_123"
        )
        logger.success(f"✓ Создан тестовый запрос с ID: {test_request.id}")
        
        # Обновляем статус
        db_ops.update_request_status(
            test_request.id,
            ProcessingStatus.COMPLETED,
            instructions={"test": "data", "components": []},
            processing_time=2.5
        )
        logger.success("✓ Обновлен статус запроса")
        
        # Создаем инструкцию
        instruction = db_ops.create_instruction_from_request(
            test_request.id,
            "Тестовая инструкция"
        )
        logger.success(f"✓ Создана инструкция с ID: {instruction.id}")
        
        # Добавляем обратную связь
        feedback = db_ops.add_feedback(
            request_id=test_request.id,
            rating=5,
            comment="Отличный результат!",
            is_useful=True
        )
        logger.success("✓ Добавлена обратная связь")
        
        # Получаем статистику
        stats = db_ops.get_statistics(days=30)
        logger.success(f"✓ Получена статистика: {stats['total_requests']} запросов")
        
        logger.success("\n🎉 Все тесты пройдены успешно!")
        
    except Exception as e:
        logger.error(f"Ошибка при тестировании: {e}")
        raise
    finally:
        db.close()


def main():
    logger.info("=" * 60)
    logger.info("Инициализация базы данных AI-Architect")
    logger.info("=" * 60)
    
    # Проверяем наличие флагов
    import sys
    force_recreate = '--recreate' in sys.argv or '--force' in sys.argv
    
    if force_recreate:
        logger.warning("Запущен режим пересоздания БД")
    
    # Создаем/обновляем БД
    create_database(force_recreate=force_recreate)
    
    # Показываем статистику
    show_database_stats()
    
    # Тестируем только если это новая БД
    response = input("\nХотите добавить тестовые данные? (y/n): ")
    if response.lower() == 'y':
        test_database()
    
    logger.info("\n" + "=" * 60)
    logger.info("Готово! База данных готова к использованию.")
    logger.info("Запустите приложение командой: streamlit run src/web/app.py")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()