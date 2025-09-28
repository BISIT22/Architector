"""
Модуль для работы с моделью Gemma через Ollama
Автор: Алексей Марышев
"""

import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import ollama
from dotenv import load_dotenv
from loguru import logger
import base64
from pathlib import Path
import requests

# Загружаем переменные окружения
load_dotenv()

@dataclass
class ArchitecturePrompt:
    """Структура промпта для архитектурного объекта"""
    text_description: str
    image_path: Optional[str] = None
    style: Optional[str] = None
    materials: Optional[List[str]] = None
    dimensions: Optional[Dict[str, float]] = None
    
class GemmaArchitect:
    """Класс для работы с моделью Gemma для генерации архитектуры"""
    
    def __init__(self):
        self.host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.model = os.getenv('OLLAMA_MODEL', 'gemma3:4b')
        self.client = ollama.Client(host=self.host)
        self.max_retries = int(os.getenv('MAX_RETRIES', '3'))
        
        logger.info(f"Инициализация GemmaArchitect с моделью {self.model}")
        
        # Проверяем доступность модели
        self._check_model_availability()
    
    def _check_model_availability(self):
        """Проверка доступности модели"""
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=10)
            response.raise_for_status()
            models = response.json()
            
            logger.info(f"OLLAMA MODELS RESPONSE: {models}")
            
            available_models = [m['name'] for m in models['models']]
            
            if self.model not in available_models:
                logger.warning(f"Модель {self.model} не найдена. Доступные модели: {available_models}")
                if available_models:
                    self.model = available_models[0]
                    logger.info(f"Используется модель: {self.model}")
                else:
                    raise ValueError("Нет доступных моделей в Ollama")
        except Exception as e:
            logger.error(f"Ошибка при проверке моделей: {e}")
            raise
    
    def _encode_image(self, image_path: str) -> str:
        """Кодирование изображения в base64"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Ошибка при кодировании изображения {image_path}: {e}")
            return ""
    
    def generate_architecture_instructions(self, prompt: ArchitecturePrompt) -> Dict[str, Any]:
        """
        Генерация инструкций для создания архитектурного объекта
        
        Args:
            prompt: Промпт с описанием архитектурного объекта
            
        Returns:
            Словарь с инструкциями для Blender
        """
        logger.info("Генерация инструкций для архитектурного объекта")
        
        # Формируем системный промпт
        system_prompt = """Ты - AI архитектор, специализирующийся на создании 3D моделей зданий.
        Твоя задача - проанализировать описание архитектурного объекта и сгенерировать детальные инструкции
        для создания 3D модели в Blender.
        
        Ответ должен быть в формате JSON со следующей структурой:
        {
            "object_type": "тип объекта (здание/мост/башня)",
            "style": "архитектурный стиль",
            "components": [
                {
                    "name": "название компонента",
                    "type": "тип примитива (cube/cylinder/sphere/plane)",
                    "position": [x, y, z],
                    "scale": [x, y, z],
                    "rotation": [x, y, z],
                    "material": "материал"
                }
            ],
            "modifiers": [
                {
                    "component": "название компонента",
                    "type": "тип модификатора",
                    "parameters": {}
                }
            ]
        }
        """
        
        # Формируем пользовательский промпт
        user_message = f"Создай инструкции для 3D модели:\n"
        user_message += f"Описание: {prompt.text_description}\n"
        
        if prompt.style:
            user_message += f"Стиль: {prompt.style}\n"
        
        if prompt.materials:
            user_message += f"Материалы: {', '.join(prompt.materials)}\n"
        
        if prompt.dimensions:
            user_message += f"Размеры: {json.dumps(prompt.dimensions)}\n"
        
        # Добавляем изображение если есть
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        if prompt.image_path and Path(prompt.image_path).exists():
            image_data = self._encode_image(prompt.image_path)
            if image_data:
                messages[-1]["images"] = [image_data]
        
        # Генерируем ответ
        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
                format="json"
            )
            
            result = response['message']['content']
            
            # Пробуем распарсить JSON
            try:
                instructions = json.loads(result)
                logger.success("Инструкции успешно сгенерированы")
                return instructions
            except json.JSONDecodeError:
                logger.warning("Не удалось распарсить JSON, возвращаем текстовый ответ")
                return {"raw_response": result}
                
        except Exception as e:
            logger.error(f"Ошибка при генерации инструкций: {e}")
            raise
    
    def analyze_architecture_image(self, image_path: str) -> Dict[str, Any]:
        """
        Анализ изображения архитектурного объекта
        
        Args:
            image_path: Путь к изображению
            
        Returns:
            Словарь с анализом изображения
        """
        logger.info(f"Анализ изображения: {image_path}")
        
        if not Path(image_path).exists():
            raise FileNotFoundError(f"Изображение не найдено: {image_path}")
        
        prompt = """Проанализируй это изображение архитектурного объекта и опиши:
        1. Тип объекта (здание, мост, башня и т.д.)
        2. Архитектурный стиль
        3. Основные структурные элементы
        4. Примерные пропорции и геометрию
        5. Видимые материалы
        
        Ответ в формате JSON:
        {
            "object_type": "",
            "style": "",
            "elements": [],
            "geometry": "",
            "materials": [],
            "description": ""
        }
        """
        
        image_data = self._encode_image(image_path)
        
        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt, "images": [image_data]}
                ],
                format="json"
            )
            
            result = response['message']['content']
            
            try:
                analysis = json.loads(result)
                logger.success("Анализ изображения завершен")
                return analysis
            except json.JSONDecodeError:
                return {"raw_analysis": result}
                
        except Exception as e:
            logger.error(f"Ошибка при анализе изображения: {e}")
            raise
    
    def refine_instructions(self, instructions: Dict, feedback: str) -> Dict[str, Any]:
        """
        Улучшение инструкций на основе обратной связи
        
        Args:
            instructions: Текущие инструкции
            feedback: Обратная связь о результате
            
        Returns:
            Улучшенные инструкции
        """
        logger.info("Улучшение инструкций на основе обратной связи")
        
        prompt = f"""На основе следующих инструкций была создана 3D модель:
        {json.dumps(instructions, indent=2)}
        
        Получена следующая обратная связь:
        {feedback}
        
        Улучши инструкции, чтобы исправить указанные проблемы.
        Верни обновленные инструкции в том же JSON формате.
        """
        
        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                format="json"
            )
            
            result = response['message']['content']
            
            try:
                refined = json.loads(result)
                logger.success("Инструкции улучшены")
                return refined
            except json.JSONDecodeError:
                logger.warning("Не удалось распарсить улучшенные инструкции")
                return instructions
                
        except Exception as e:
            logger.error(f"Ошибка при улучшении инструкций: {e}")
            return instructions

# Функция для тестирования
def test_ai_model():
    """Тестирование модуля AI"""
    architect = GemmaArchitect()
    
    # Тест генерации инструкций
    prompt = ArchitecturePrompt(
        text_description="Современное офисное здание, 5 этажей, стеклянный фасад",
        style="Модерн",
        materials=["стекло", "бетон", "металл"],
        dimensions={"height": 20, "width": 30, "depth": 25}
    )
    
    instructions = architect.generate_architecture_instructions(prompt)
    logger.info(f"Сгенерированные инструкции: {json.dumps(instructions, indent=2)}")
    
    return instructions

if __name__ == "__main__":
    test_ai_model()