from pathlib import Path
import time
from PIL import Image

def save_and_create_thumbnail(uploaded_file, upload_dir="data/uploads", thumb_dir="data/thumbnails", thumb_size=(128, 128)):
    """
    Сохраняет загруженный файл, создает его уменьшенную копию и возвращает пути.
    """
    # Создаем директории, если их нет
    upload_path = Path(upload_dir)
    thumb_path = Path(thumb_dir)
    upload_path.mkdir(parents=True, exist_ok=True)
    thumb_path.mkdir(parents=True, exist_ok=True)

    # Генерируем уникальное имя файла
    timestamp = int(time.time())
    extension = Path(uploaded_file.name).suffix
    base_filename = f"{timestamp}_{Path(uploaded_file.name).stem}{extension}"
    
    original_filepath = upload_path / base_filename
    thumbnail_filepath = thumb_path / base_filename

    # Сохраняем оригинальный файл
    with open(original_filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Создаем и сохраняем thumbnail
    try:
        with Image.open(original_filepath) as img:
            img.thumbnail(thumb_size)
            img.save(thumbnail_filepath)
    except Exception as e:
        print(f"Could not create thumbnail for {original_filepath}: {e}")
        return str(original_filepath), None


    return str(original_filepath), str(thumbnail_filepath)
