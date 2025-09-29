"""
Веб-интерфейс на Streamlit для AI-архитектора
Автор: Алексей Марышев
"""

import streamlit as st
from pathlib import Path
import os
import sys
import json
import time
from loguru import logger

# Добавляем корневую директорию в sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT_DIR))

from src.core.ai_model import GemmaArchitect, ArchitecturePrompt
from src.database.connection import get_db, init_db
from src.database.models import (
    Base, GeneratedInstruction, GenerationRequest,
    ProcessingStatus, RequestType, UserFeedback
)
from src.database.operations import DatabaseOperations, get_db_operations
from src.visualization.web_3d_viewer import Web3DViewer
from sqlalchemy.orm import Session
import uuid

st.set_page_config(layout="wide", page_title="AI Architect", page_icon="🏗️")

# --- Стили и анимации ---
st.markdown("""
<style>
    /* Плавное появление элементов */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .stApp > div {
        animation: fadeIn 0.5s ease-in-out;
    }
    /* Кастомный стиль для кнопок */
    .stButton>button {
        border-radius: 12px;
        border: 2px solid #4CAF50;
        color: white;
        background-color: #4CAF50;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: white;
        color: #4CAF50;
        border-color: #4CAF50;
    }
</style>
""", unsafe_allow_html=True)


# --- Кэширование ресурсов ---
@st.cache_resource
def get_ai_architect():
    return GemmaArchitect()

@st.cache_resource
def get_database_session():
    db_path = ROOT_DIR / "data" / "architect.db"
    
    # Создаем директорию если её нет
    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Инициализация БД только если её нет
    if not db_path.exists():
        logger.info("База данных не найдена, создаем новую...")
        init_db()
        st.toast("База данных успешно создана!", icon="✔️")
    else:
        # Проверяем, что таблицы существуют
        from sqlalchemy import inspect
        from src.database.connection import engine
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        # Если таблиц нет или их меньше чем должно быть, создаем их
        expected_tables = ['generation_requests', 'generated_instructions', 'user_feedback', 'refinement_history', 'system_stats']
        missing_tables = set(expected_tables) - set(tables)
        
        if missing_tables:
            logger.info(f"Обнаружены отсутствующие таблицы: {missing_tables}. Создаем...")
            init_db()
            st.toast("База данных обновлена!", icon="🔄")
        else:
            logger.info(f"База данных загружена. Таблиц: {len(tables)}")
        
    return next(get_db())

# --- Основная логика --- 
def main():
    # Логотип и заголовок
    st.markdown("""
    <div style="text-align: center;">
        <h1>🏗️ AI Architect</h1>
        <p>Ваш персональный помощник для генерации архитектурных концепций</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # Генерируем ID сессии пользователя
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    
    menu = [
        "🚀 Генерация Инструкций",
        "🎮 3D Галерея",
        "📊 История запросов", 
        "📈 Аналитика",
        "⭐ Избранное",
        "🔍 Поиск",
        "📝 Обратная связь"
    ]
    choice = st.sidebar.selectbox("Меню", menu)
    db_session = get_database_session()
    db_ops = get_db_operations(db_session)

    if choice == "🚀 Генерация Инструкций":
        render_generation_page(db_session, db_ops)
    elif choice == "🎮 3D Галерея":
        render_3d_gallery_page(db_ops)
    elif choice == "📊 История запросов":
        render_history_page(db_ops)
    elif choice == "📈 Аналитика":
        render_analytics_page(db_ops)
    elif choice == "⭐ Избранное":
        render_favorites_page(db_ops)
    elif choice == "🔍 Поиск":
        render_search_page(db_ops)
    elif choice == "📝 Обратная связь":
        render_feedback_page(db_ops)

def render_generation_page(db: Session, db_ops: DatabaseOperations):
    st.header("Новая Архитектурная Концепция")

    col1, col2 = st.columns([0.6, 0.4])

    with col1:
        st.subheader("Параметры Запроса")
        with st.form(key="generation_form"):
            text_description = st.text_area("Опишите вашу идею", height=200, placeholder="Например: современный двухэтажный дом в стиле минимализм, с плоской крышей и панорамными окнами...")
            style = st.text_input("Архитектурный стиль", placeholder="Минимализм, Лофт, Хай-тек...")
            materials = st.text_input("Основные материалы", placeholder="Бетон, стекло, дерево...")
            submit_button = st.form_submit_button(label="✨ Сгенерировать Инструкции")

        if submit_button and text_description:
            # Создаем запрос в БД
            try:
                request = db_ops.create_generation_request(
                    input_prompt=text_description,
                    request_type=RequestType.TEXT_GENERATION,
                    style=style,
                    materials=materials.split(",") if materials else None,
                    user_session_id=st.session_state.session_id
                )
                
                # Обновляем статус на "в обработке"
                db_ops.update_request_status(request.id, ProcessingStatus.PROCESSING)
                
                architect = get_ai_architect()
                prompt = ArchitecturePrompt(
                    text_description=text_description,
                    style=style,
                    materials=materials.split(",") if materials else None
                )
                
                # Анимация загрузки
                with st.spinner('Искусственный интеллект творит магию... 🧙‍♂️'):
                    start_time = time.time()
                    instructions = architect.generate_architecture_instructions(prompt)
                    processing_time = time.time() - start_time
                    st.session_state['instructions'] = instructions
                
                # Обновляем запрос с результатом
                db_ops.update_request_status(
                    request.id,
                    ProcessingStatus.COMPLETED,
                    instructions=instructions,
                    processing_time=processing_time
                )
                
                # Создаем запись в таблице инструкций (для совместимости)
                instruction_entry = db_ops.create_instruction_from_request(
                    request_id=request.id,
                    name=text_description[:50]
                )
                
                st.success("Инструкции успешно сгенерированы!")
                st.balloons()
                st.toast(f"Концепция сохранена! ID запроса: {request.id}", icon="💾")
                
            except Exception as e:
                st.error(f"Ошибка: {e}")
                if 'request' in locals():
                    db_ops.update_request_status(
                        request.id,
                        ProcessingStatus.FAILED,
                        error_message=str(e)
                    )
        elif submit_button:
            st.warning("Пожалуйста, опишите вашу идею, чтобы AI мог начать работу.")

    with col2:
        st.subheader("Результат Генерации")
        if 'instructions' in st.session_state:
            # Показываем JSON в расширяемом виде
            with st.expander("📋 Показать полные инструкции", expanded=True):
                # Форматируем JSON для лучшей читаемости
                import json
                formatted_json = json.dumps(st.session_state['instructions'], indent=2, ensure_ascii=False)
                
                # Показываем в текстовом поле с возможностью копирования
                st.code(formatted_json, language='json')
                
                # Дополнительно показываем основные элементы
                if isinstance(st.session_state['instructions'], dict):
                    st.markdown("### 📊 Структура результата:")
                    
                    # Показываем тип объекта
                    if 'object_type' in st.session_state['instructions']:
                        st.markdown(f"**Тип объекта:** {st.session_state['instructions']['object_type']}")
                    
                    # Показываем стиль
                    if 'style' in st.session_state['instructions']:
                        st.markdown(f"**Стиль:** {st.session_state['instructions']['style']}")
                    
                    # Показываем количество компонентов
                    if 'components' in st.session_state['instructions']:
                        components = st.session_state['instructions']['components']
                        st.markdown(f"**Количество компонентов:** {len(components)}")
                        
                        # Показываем список компонентов
                        if components:
                            st.markdown("**Компоненты:**")
                            for i, comp in enumerate(components, 1):
                                comp_name = comp.get('name', f'Компонент {i}')
                                comp_type = comp.get('type', 'неизвестный')
                                st.markdown(f"  {i}. {comp_name} ({comp_type})")
                    
                    # Показываем модификаторы если есть
                    if 'modifiers' in st.session_state['instructions']:
                        modifiers = st.session_state['instructions']['modifiers']
                        if modifiers:
                            st.markdown(f"**Модификаторы:** {len(modifiers)}")
            
            # Кнопки действий
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            with col_btn1:
                # Кнопка для скачивания JSON
                download_json = json.dumps(st.session_state['instructions'], indent=2, ensure_ascii=False)
                st.download_button(
                    label="📥 Скачать JSON",
                    data=download_json,
                    file_name="instructions.json",
                    mime="application/json"
                )
            
            with col_btn2:
                if st.button("🎮 Показать 3D модель", type="primary"):
                    st.session_state['show_3d'] = True
            
            with col_btn3:
                if st.button("🗑️ Очистить"):
                    del st.session_state['instructions']
                    if 'show_3d' in st.session_state:
                        del st.session_state['show_3d']
                    st.rerun()
            
            # Отображаем 3D модель если нажата кнопка
            if st.session_state.get('show_3d', False):
                st.markdown("---")
                st.markdown("### 🎮 3D Визуализация")
                st.info("💡 Используйте мышь для вращения модели, колесико для масштабирования")
                
                try:
                    Web3DViewer.render_3d_view(st.session_state['instructions'])
                except Exception as e:
                    st.error(f"Ошибка при отображении 3D модели: {e}")
                    st.info("Попробуйте сгенерировать новые инструкции с более подробным описанием компонентов")
        else:
            st.info("Здесь появятся сгенерированные инструкции после выполнения запроса.")

def render_database_page(db: Session):
    st.header("Архив Сгенерированных Концепций")
    
    try:
        all_instructions = db.query(GeneratedInstruction).order_by(GeneratedInstruction.created_at.desc()).all()
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")
        st.warning("Возможно, база данных еще пуста. Попробуйте сгенерировать первую инструкцию.")
        return

    if not all_instructions:
        st.info("В базе данных пока нет ни одной записи. Создайте свою первую архитектурную концепцию!")
        return

    for entry in all_instructions:
        with st.expander(f"**{entry.name}** (от {entry.created_at.strftime('%Y-%m-%d %H:%M')})"):
            st.markdown("**Исходный запрос:**")
            st.text(entry.input_prompt)
            st.markdown("**Сгенерированные инструкции (JSON):**")
            st.json(entry.instructions)


def render_history_page(db_ops: DatabaseOperations):
    """Страница истории запросов"""
    st.header("📊 История запросов")
    
    # Фильтры
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox(
            "Статус",
            ["Все", "Завершенные", "В обработке", "С ошибкой"],
            key="status_filter"
        )
    with col2:
        session_only = st.checkbox("Только моя сессия", key="session_filter")
    with col3:
        limit = st.number_input("Количество записей", min_value=10, max_value=100, value=20)
    
    # Получаем данные
    status_map = {
        "Завершенные": ProcessingStatus.COMPLETED,
        "В обработке": ProcessingStatus.PROCESSING,
        "С ошибкой": ProcessingStatus.FAILED
    }
    
    requests = db_ops.get_all_requests(
        limit=limit,
        status=status_map.get(status_filter),
        user_session_id=st.session_state.session_id if session_only else None
    )
    
    if not requests:
        st.info("История запросов пуста")
        return
    
    # Отображаем запросы
    for req in requests:
        status_icon = {
            ProcessingStatus.COMPLETED: "✅",
            ProcessingStatus.PROCESSING: "⏳",
            ProcessingStatus.FAILED: "❌",
            ProcessingStatus.PENDING: "⏸️"
        }.get(req.status, "❓")
        
        with st.expander(f"{status_icon} {req.input_prompt[:50]}... | {req.created_at.strftime('%Y-%m-%d %H:%M') if req.created_at else 'N/A'}"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("**Запрос:**")
                st.text(req.input_prompt)
                
                if req.style:
                    st.markdown(f"**Стиль:** {req.style}")
                if req.materials:
                    st.markdown(f"**Материалы:** {', '.join(req.materials)}")
                    
            with col2:
                st.markdown("**Информация:**")
                st.markdown(f"ID: {req.id}")
                st.markdown(f"Статус: {req.status.value}")
                if req.processing_time:
                    st.markdown(f"Время: {req.processing_time:.2f} сек")
                    
            if req.generated_instructions:
                st.markdown("**Результат:**")
                # Отображаем JSON в раскрывающемся блоке
                with st.expander("Показать инструкции JSON"):
                    import json
                    formatted_json = json.dumps(req.generated_instructions, indent=2, ensure_ascii=False)
                    st.code(formatted_json, language='json')
                    
                    # Кнопка скачивания
                    st.download_button(
                        label="📥 Скачать JSON",
                        data=formatted_json,
                        file_name=f"instructions_{req.id}.json",
                        mime="application/json",
                        key=f"download_{req.id}"
                    )
                
            if req.error_message:
                st.error(f"Ошибка: {req.error_message}")
                
            # Действия
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button(f"🗑️ Удалить", key=f"del_{req.id}"):
                    if db_ops.delete_request(req.id):
                        st.success("Запрос удален")
                        st.rerun()
            with col2:
                if req.status == ProcessingStatus.COMPLETED:
                    if st.button(f"⭐ В избранное", key=f"fav_{req.id}"):
                        # Создаем инструкцию если ее нет
                        try:
                            instruction = db_ops.create_instruction_from_request(
                                req.id, 
                                req.input_prompt[:50]
                            )
                            db_ops.toggle_favorite(instruction.id)
                            st.success("Добавлено в избранное")
                        except:
                            st.error("Ошибка при добавлении в избранное")


def render_analytics_page(db_ops: DatabaseOperations):
    """Страница аналитики"""
    st.header("📈 Аналитика системы")
    
    # Выбор периода
    period = st.selectbox(
        "Период анализа",
        ["Последние 7 дней", "Последние 30 дней", "Последние 90 дней"],
        key="analytics_period"
    )
    
    days_map = {"Последние 7 дней": 7, "Последние 30 дней": 30, "Последние 90 дней": 90}
    stats = db_ops.get_statistics(days_map[period])
    
    # Основные метрики
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Всего запросов", stats['total_requests'])
    with col2:
        st.metric("Успешность", f"{stats['successful_rate']}%")
    with col3:
        st.metric("Среднее время", f"{stats['average_processing_time']} сек")
    with col4:
        st.metric("Уникальных сессий", stats['unique_sessions'])
    
    st.markdown("---")
    
    # Графики
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Распределение по статусам")
        if stats['status_breakdown']:
            import pandas as pd
            df_status = pd.DataFrame(
                list(stats['status_breakdown'].items()),
                columns=['Статус', 'Количество']
            )
            st.bar_chart(df_status.set_index('Статус'))
    
    with col2:
        st.subheader("Типы запросов")
        if stats['request_types']:
            import pandas as pd
            df_types = pd.DataFrame(
                list(stats['request_types'].items()),
                columns=['Тип', 'Количество']
            )
            st.bar_chart(df_types.set_index('Тип'))
    
    # Популярные стили
    st.subheader("Популярные архитектурные стили")
    popular_styles = db_ops.get_popular_styles(10)
    if popular_styles:
        import pandas as pd
        df_styles = pd.DataFrame(popular_styles)
        st.bar_chart(df_styles.set_index('style'))
    else:
        st.info("Недостаточно данных для анализа стилей")
    
    # Последняя активность
    st.subheader("Последняя активность (24 часа)")
    recent = db_ops.get_recent_activity(24)
    if recent:
        for activity in recent[:5]:
            status_emoji = "✅" if activity['status'] == 'completed' else "❌" if activity['status'] == 'failed' else "⏳"
            st.markdown(f"{status_emoji} **{activity['prompt_preview']}**")
            st.caption(f"ID: {activity['id']} | {activity['created_at']}")
    else:
        st.info("Нет активности за последние 24 часа")


def render_favorites_page(db_ops: DatabaseOperations):
    """Страница избранных инструкций"""
    st.header("⭐ Избранные концепции")
    
    favorites = db_ops.get_all_instructions(is_favorite=True)
    
    if not favorites:
        st.info("У вас пока нет избранных концепций")
        st.markdown("💡 *Добавляйте понравившиеся результаты в избранное из истории запросов*")
        return
    
    for fav in favorites:
        with st.expander(f"⭐ {fav.name} | {fav.created_at.strftime('%Y-%m-%d') if fav.created_at else 'N/A'}"):
            st.markdown("**Исходный запрос:**")
            st.text(fav.input_prompt)
            
            st.markdown("**Инструкции:**")
            # Отображаем в текстовом поле с возможностью копирования
            import json
            formatted_json = json.dumps(fav.instructions, indent=2, ensure_ascii=False)
            st.code(formatted_json, language='json')
            
            # Кнопка скачивания
            st.download_button(
                label="📥 Скачать JSON",
                data=formatted_json,
                file_name=f"favorite_{fav.id}.json",
                mime="application/json",
                key=f"download_fav_{fav.id}"
            )
            
            if fav.tags:
                st.markdown(f"**Теги:** {', '.join(fav.tags)}")
            
            if st.button(f"Удалить из избранного", key=f"unfav_{fav.id}"):
                db_ops.toggle_favorite(fav.id)
                st.success("Удалено из избранного")
                st.rerun()


def render_search_page(db_ops: DatabaseOperations):
    """Страница поиска"""
    st.header("🔍 Поиск запросов")
    
    search_query = st.text_input(
        "Введите текст для поиска",
        placeholder="Например: современный дом, минимализм, стекло..."
    )
    
    if search_query:
        with st.spinner("Поиск..."):
            results = db_ops.search_requests(search_query)
        
        if results:
            st.success(f"Найдено {len(results)} результатов")
            
            for req in results:
                with st.expander(f"📋 {req.input_prompt[:70]}..."):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown("**Полный запрос:**")
                        st.text(req.input_prompt)
                        
                        if req.style:
                            st.markdown(f"**Стиль:** {req.style}")
                    
                    with col2:
                        st.markdown(f"**ID:** {req.id}")
                        st.markdown(f"**Дата:** {req.created_at.strftime('%Y-%m-%d') if req.created_at else 'N/A'}")
                    
                    if req.generated_instructions:
                        with st.expander("Показать инструкции"):
                            import json
                            formatted_json = json.dumps(req.generated_instructions, indent=2, ensure_ascii=False)
                            st.code(formatted_json, language='json')
                            
                            # Кнопка скачивания
                            st.download_button(
                                label="📥 Скачать",
                                data=formatted_json,
                                file_name=f"search_result_{req.id}.json",
                                mime="application/json",
                                key=f"download_search_{req.id}"
                            )
        else:
            st.info("Ничего не найдено. Попробуйте другой запрос.")


def render_feedback_page(db_ops: DatabaseOperations):
    """Страница обратной связи"""
    st.header("📝 Обратная связь")
    
    st.markdown("""
    Помогите нам улучшить систему! Оставьте отзыв о последних сгенерированных инструкциях.
    """)
    
    # Получаем последние завершенные запросы пользователя
    recent_requests = db_ops.get_all_requests(
        limit=10,
        status=ProcessingStatus.COMPLETED,
        user_session_id=st.session_state.session_id
    )
    
    if not recent_requests:
        st.info("У вас пока нет завершенных запросов для оценки")
        return
    
    selected_request = st.selectbox(
        "Выберите запрос для оценки",
        recent_requests,
        format_func=lambda x: f"{x.id}: {x.input_prompt[:50]}..."
    )
    
    if selected_request:
        st.markdown("### Детали запроса")
        with st.expander("Показать результат"):
            import json
            formatted_json = json.dumps(selected_request.generated_instructions, indent=2, ensure_ascii=False)
            st.code(formatted_json, language='json')
        
        st.markdown("### Ваша оценка")
        
        col1, col2 = st.columns(2)
        
        with col1:
            rating = st.slider(
                "Оценка качества (1-5)",
                min_value=1,
                max_value=5,
                value=3
            )
            
            is_useful = st.checkbox("Результат был полезен")
        
        with col2:
            comment = st.text_area(
                "Комментарий (необязательно)",
                placeholder="Что можно улучшить?"
            )
        
        if st.button("Отправить отзыв", type="primary"):
            feedback = db_ops.add_feedback(
                request_id=selected_request.id,
                rating=rating,
                comment=comment if comment else None,
                is_useful=is_useful
            )
            st.success("Спасибо за ваш отзыв! Он поможет нам стать лучше.")
            st.balloons()
            
            # Обновляем статистику
            db_ops.update_system_stats()


def render_3d_gallery_page(db_ops: DatabaseOperations):
    """Страница 3D галереи моделей"""
    st.header("🎮 3D Галерея моделей")
    
    st.markdown("""
    Здесь вы можете просматривать 3D визуализации сгенерированных архитектурных концепций.
    Выберите модель из списка для просмотра.
    """)
    
    # Получаем завершенные запросы с инструкциями
    completed_requests = db_ops.get_all_requests(
        status=ProcessingStatus.COMPLETED,
        limit=20
    )
    
    if not completed_requests:
        st.info("Пока нет завершенных запросов для визуализации")
        st.markdown("💡 Сначала сгенерируйте инструкции на странице 'Генерация Инструкций'")
        return
    
    # Выбор модели для просмотра
    selected_request = st.selectbox(
        "Выберите модель для просмотра:",
        completed_requests,
        format_func=lambda x: f"{x.id}: {x.input_prompt[:60]}..."
    )
    
    if selected_request and selected_request.generated_instructions:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### Описание")
            st.text(selected_request.input_prompt)
            
            if selected_request.style:
                st.markdown(f"**Стиль:** {selected_request.style}")
            if selected_request.materials:
                st.markdown(f"**Материалы:** {', '.join(selected_request.materials)}")
        
        with col2:
            st.markdown("### Информация")
            st.markdown(f"**ID:** {selected_request.id}")
            st.markdown(f"**Дата:** {selected_request.created_at.strftime('%Y-%m-%d %H:%M')}")
            if selected_request.processing_time:
                st.markdown(f"**Время генерации:** {selected_request.processing_time:.2f} сек")
        
        st.markdown("---")
        
        # Отображаем 3D модель
        st.markdown("### 🎮 3D Модель")
        st.info("💡 Используйте мышь для вращения, колесико для масштаба, ПКМ для перемещения")
        
        try:
            Web3DViewer.render_3d_view(selected_request.generated_instructions)
        except Exception as e:
            st.error(f"Ошибка при отображении 3D модели: {e}")
            st.info("Модель может не отображаться, если в инструкциях нет компонентов")
            
            # Показываем JSON для отладки
            with st.expander("Показать инструкции"):
                import json
                formatted_json = json.dumps(selected_request.generated_instructions, indent=2, ensure_ascii=False)
                st.code(formatted_json, language='json')


if __name__ == "__main__":
    main()
