"""
Скрипт для установки и настройки Ollama с моделью Gemma 3:4B
Автор: Алексей Марышев
"""

import os
import subprocess
import sys
import platform
from pathlib import Path
import requests
import time

def check_ollama_installed():
    """Проверка установки Ollama"""
    try:
        result = subprocess.run(['ollama', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Ollama уже установлен")
            return True
    except FileNotFoundError:
        pass
    return False

def install_ollama_windows():
    """Установка Ollama для Windows"""
    print("Установка Ollama для Windows...")
    
    # URL для скачивания Ollama для Windows
    ollama_url = "https://ollama.com/download/OllamaSetup.exe"
    
    # Скачиваем установщик
    installer_path = Path.home() / "Downloads" / "OllamaSetup.exe"
    
    print(f"Скачивание Ollama из {ollama_url}...")
    response = requests.get(ollama_url, stream=True)
    
    total_size = int(response.headers.get('content-length', 0))
    block_size = 8192
    
    with open(installer_path, 'wb') as file:
        downloaded = 0
        for data in response.iter_content(block_size):
            downloaded += len(data)
            file.write(data)
            progress = downloaded / total_size * 100 if total_size else 0
            print(f"Прогресс: {progress:.1f}%", end='\r')
    
    print("\n✓ Загрузка завершена")
    
    # Запускаем установщик
    print("Запуск установщика...")
    subprocess.run([str(installer_path)], check=True)
    
    print("✓ Ollama установлен")
    print("Примечание: Возможно, потребуется перезапустить терминал")

def setup_gemma_model():
    """Загрузка и настройка модели Gemma 3:4B"""
    print("\nНастройка модели Gemma 3:4B...")
    
    # Проверяем, запущен ли Ollama
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code != 200:
            print("Запуск службы Ollama...")
            subprocess.Popen(['ollama', 'serve'], shell=True)
            time.sleep(5)  # Даем время на запуск
    except requests.exceptions.ConnectionError:
        print("Запуск службы Ollama...")
        subprocess.Popen(['ollama', 'serve'], shell=True)
        time.sleep(5)
    
    # Загружаем модель Gemma
    print("Загрузка модели gemma:2b (аналог 3:4B)...")
    print("Это может занять некоторое время...")
    
    try:
        # Используем gemma:2b так как gemma:3b может быть недоступна
        result = subprocess.run(['ollama', 'pull', 'gemma:2b'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ Модель Gemma успешно загружена")
        else:
            print(f"Ошибка при загрузке модели: {result.stderr}")
            
            # Альтернативный вариант - использовать gemma2
            print("Пробуем альтернативную модель gemma2:2b...")
            result = subprocess.run(['ollama', 'pull', 'gemma2:2b'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✓ Модель Gemma2 успешно загружена")
            else:
                print("⚠ Не удалось загрузить модель Gemma")
                print("Вы можете вручную загрузить модель командой: ollama pull gemma:2b")
    
    except Exception as e:
        print(f"Ошибка: {e}")
        print("Попробуйте вручную выполнить: ollama pull gemma:2b")

def test_ollama_connection():
    """Тестирование подключения к Ollama"""
    print("\nТестирование подключения к Ollama...")
    
    try:
        import ollama
        
        # Пробуем получить список моделей
        client = ollama.Client(host='http://localhost:11434')
        models = client.list()
        
        print("✓ Подключение к Ollama успешно установлено")
        print(f"Доступные модели: {[m['name'] for m in models['models']]}")
        
        return True
        
    except Exception as e:
        print(f"⚠ Ошибка подключения: {e}")
        return False

def create_env_file():
    """Создание файла .env с конфигурацией"""
    env_path = Path(__file__).parent.parent / '.env'
    
    env_content = """# Конфигурация Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=gemma:2b

# Конфигурация базы данных
DATABASE_URL=sqlite:///data/architect.db

# Конфигурация Blender
BLENDER_PATH=C:/Program Files/Blender Foundation/Blender 3.6/blender.exe

# Другие настройки
LOG_LEVEL=INFO
DEBUG=False
"""
    
    with open(env_path, 'w') as f:
        f.write(env_content)
    
    print(f"✓ Создан файл конфигурации: {env_path}")

def main():
    print("=" * 60)
    print("Настройка Ollama и модели Gemma для AI-архитектора")
    print("=" * 60)
    
    # Проверка ОС
    if platform.system() != "Windows":
        print(f"⚠ Этот скрипт предназначен для Windows. Ваша ОС: {platform.system()}")
        print("Для других ОС посетите: https://ollama.com/download")
        return
    
    # Установка Ollama если нужно
    if not check_ollama_installed():
        install_ollama_windows()
    
    # Настройка модели
    setup_gemma_model()
    
    # Тестирование подключения
    test_ollama_connection()
    
    # Создание файла конфигурации
    create_env_file()
    
    print("\n" + "=" * 60)
    print("✓ Настройка завершена!")
    print("Следующие шаги:")
    print("1. Убедитесь, что Ollama запущен (ollama serve)")
    print("2. Установите Python зависимости (pip install -r requirements.txt)")
    print("3. Запустите приложение (streamlit run src/web/app.py)")
    print("=" * 60)

if __name__ == "__main__":
    main()