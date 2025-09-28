"""
Модуль для обработки изображений архитектурных объектов
Автор: Алексей Марышев
"""

import os
from typing import Tuple, List, Optional, Dict, Any
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
from pathlib import Path
from loguru import logger
import cv2

class ImageProcessor:
    """Класс для обработки изображений архитектурных объектов"""
    
    def __init__(self, data_dir: str = "data/training_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
        
        logger.info(f"Инициализация ImageProcessor с директорией {self.data_dir}")
    
    def load_image(self, image_path: str) -> Image.Image:
        """
        Загрузка изображения
        
        Args:
            image_path: Путь к изображению
            
        Returns:
            Объект изображения PIL
        """
        path = Path(image_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Изображение не найдено: {image_path}")
        
        if path.suffix.lower() not in self.supported_formats:
            raise ValueError(f"Неподдерживаемый формат: {path.suffix}")
        
        try:
            image = Image.open(image_path)
            logger.info(f"Загружено изображение: {image_path}, размер: {image.size}")
            return image
        except Exception as e:
            logger.error(f"Ошибка при загрузке изображения: {e}")
            raise
    
    def preprocess_image(self, image: Image.Image, target_size: Tuple[int, int] = (512, 512)) -> Image.Image:
        """
        Предобработка изображения
        
        Args:
            image: Изображение PIL
            target_size: Целевой размер
            
        Returns:
            Обработанное изображение
        """
        logger.info(f"Предобработка изображения, целевой размер: {target_size}")
        
        # Изменяем размер с сохранением пропорций
        image.thumbnail(target_size, Image.Resampling.LANCZOS)
        
        # Создаем новое изображение с заданным размером
        new_image = Image.new('RGB', target_size, (255, 255, 255))
        
        # Вставляем изображение по центру
        paste_x = (target_size[0] - image.size[0]) // 2
        paste_y = (target_size[1] - image.size[1]) // 2
        new_image.paste(image, (paste_x, paste_y))
        
        return new_image
    
    def enhance_image(self, image: Image.Image) -> Image.Image:
        """
        Улучшение качества изображения
        
        Args:
            image: Изображение PIL
            
        Returns:
            Улучшенное изображение
        """
        logger.info("Улучшение качества изображения")
        
        # Увеличиваем контрастность
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.2)
        
        # Увеличиваем резкость
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.1)
        
        # Применяем легкое размытие для удаления шума
        image = image.filter(ImageFilter.MedianFilter(size=3))
        
        return image
    
    def extract_edges(self, image_path: str) -> np.ndarray:
        """
        Извлечение границ из изображения (для анализа структуры)
        
        Args:
            image_path: Путь к изображению
            
        Returns:
            Массив с границами
        """
        logger.info(f"Извлечение границ из {image_path}")
        
        # Загружаем изображение в OpenCV
        img = cv2.imread(str(image_path))
        
        if img is None:
            raise ValueError(f"Не удалось загрузить изображение: {image_path}")
        
        # Преобразуем в градации серого
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Применяем детектор границ Canny
        edges = cv2.Canny(gray, 50, 150)
        
        return edges
    
    def detect_lines(self, image_path: str) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """
        Обнаружение линий в изображении (для анализа структуры здания)
        
        Args:
            image_path: Путь к изображению
            
        Returns:
            Список линий в формате ((x1, y1), (x2, y2))
        """
        logger.info(f"Обнаружение линий в {image_path}")
        
        # Загружаем изображение
        img = cv2.imread(str(image_path))
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Обнаруживаем границы
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # Используем преобразование Хафа для обнаружения линий
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=100, maxLineGap=10)
        
        detected_lines = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                detected_lines.append(((x1, y1), (x2, y2)))
        
        logger.info(f"Обнаружено {len(detected_lines)} линий")
        return detected_lines
    
    def analyze_perspective(self, image_path: str) -> Dict[str, Any]:
        """
        Анализ перспективы изображения
        
        Args:
            image_path: Путь к изображению
            
        Returns:
            Словарь с параметрами перспективы
        """
        logger.info(f"Анализ перспективы {image_path}")
        
        lines = self.detect_lines(image_path)
        
        # Группируем линии по углам наклона
        vertical_lines = []
        horizontal_lines = []
        diagonal_lines = []
        
        for (x1, y1), (x2, y2) in lines:
            angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
            
            if angle < 10 or angle > 170:
                horizontal_lines.append(((x1, y1), (x2, y2)))
            elif 80 < angle < 100:
                vertical_lines.append(((x1, y1), (x2, y2)))
            else:
                diagonal_lines.append(((x1, y1), (x2, y2)))
        
        return {
            "total_lines": len(lines),
            "vertical_lines": len(vertical_lines),
            "horizontal_lines": len(horizontal_lines),
            "diagonal_lines": len(diagonal_lines),
            "has_perspective": len(diagonal_lines) > 5
        }
    
    def save_processed_image(self, image: Image.Image, name: str, subfolder: str = "processed") -> str:
        """
        Сохранение обработанного изображения
        
        Args:
            image: Изображение PIL
            name: Имя файла
            subfolder: Подпапка для сохранения
            
        Returns:
            Путь к сохраненному файлу
        """
        save_dir = self.data_dir / subfolder
        save_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = save_dir / f"{name}.png"
        image.save(file_path)
        
        logger.info(f"Изображение сохранено: {file_path}")
        return str(file_path)
    
    def batch_process(self, image_folder: str, target_size: Tuple[int, int] = (512, 512)) -> List[str]:
        """
        Пакетная обработка изображений
        
        Args:
            image_folder: Папка с изображениями
            target_size: Целевой размер
            
        Returns:
            Список путей к обработанным изображениям
        """
        folder = Path(image_folder)
        
        if not folder.exists():
            raise ValueError(f"Папка не существует: {image_folder}")
        
        processed_images = []
        
        for image_file in folder.iterdir():
            if image_file.suffix.lower() in self.supported_formats:
                try:
                    # Загружаем и обрабатываем изображение
                    img = self.load_image(str(image_file))
                    img = self.preprocess_image(img, target_size)
                    img = self.enhance_image(img)
                    
                    # Сохраняем
                    save_path = self.save_processed_image(img, image_file.stem)
                    processed_images.append(save_path)
                    
                except Exception as e:
                    logger.error(f"Ошибка при обработке {image_file}: {e}")
        
        logger.info(f"Обработано {len(processed_images)} изображений")
        return processed_images

# Функция для тестирования
def test_image_processor():
    """Тестирование модуля обработки изображений"""
    processor = ImageProcessor()
    
    # Создаем тестовое изображение
    test_image = Image.new('RGB', (800, 600), color=(100, 150, 200))
    
    # Добавляем простые геометрические фигуры для имитации здания
    from PIL import ImageDraw
    draw = ImageDraw.Draw(test_image)
    
    # Рисуем "здание"
    draw.rectangle([200, 200, 600, 500], fill=(150, 150, 150), outline=(0, 0, 0))
    # Окна
    for i in range(3):
        for j in range(4):
            x = 250 + j * 80
            y = 250 + i * 80
            draw.rectangle([x, y, x+40, y+40], fill=(200, 200, 255), outline=(0, 0, 0))
    
    # Сохраняем тестовое изображение
    test_path = processor.save_processed_image(test_image, "test_building", "test")
    
    # Тестируем анализ
    perspective = processor.analyze_perspective(test_path)
    logger.info(f"Анализ перспективы: {perspective}")
    
    return test_path

if __name__ == "__main__":
    test_image_processor()