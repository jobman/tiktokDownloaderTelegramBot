import instaloader
import re
import os
import shutil
import time
import logging

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_shortcode_from_url(url):
    """Извлекает shortcode из URL Instagram."""
    pattern = r'(?:/p/|/reel/)([A-Za-z0-9_-]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    else:
        raise ValueError("Невалидная ссылка на Instagram")

def get_instagram_video(url, username=None, password=None):
    """Скачивает видео из Instagram и возвращает его байты."""
    try:
        # Инициализация Instaloader
        L = instaloader.Instaloader(download_pictures=False, download_comments=False, download_geotags=False)
        
        # Авторизация, если предоставлены логин и пароль
        if username and password:
            L.login(username, password)
            logger.info("Авторизация успешна")
        
        # Получение shortcode из URL
        shortcode = get_shortcode_from_url(url)
        logger.info(f"Shortcode: {shortcode}")
        
        # Абсолютный путь к папке с именем shortcode
        post_dir = os.path.normpath(os.path.join(os.getcwd(), shortcode))
        logger.info(f"Post directory: {post_dir}")
        
        # Удаляем старую папку, если существует
        if os.path.exists(post_dir):
            shutil.rmtree(post_dir, ignore_errors=True)
            logger.info(f"Removed existing post directory: {post_dir}")
        
        # Загрузка поста
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        # Проверка, является ли пост видео
        if not post.is_video:
            raise ValueError("Пост не содержит видео")
        
        # Скачиваем пост, передавая только shortcode как target
        L.download_post(post, target=shortcode)
        logger.info(f"Post downloaded to: {post_dir}")
        
        # Даём небольшую задержку, чтобы файл точно записался
        time.sleep(1)
        
        # Проверяем, существует ли папка
        if not os.path.exists(post_dir):
            raise FileNotFoundError(f"Папка поста не найдена: {post_dir}")
        
        # Логируем содержимое папки
        logger.info(f"Contents of {post_dir}: {os.listdir(post_dir)}")
        
        # Находим видеофайл в папке поста
        for file in os.listdir(post_dir):
            if file.endswith(".mp4"):
                video_path = os.path.normpath(os.path.join(post_dir, file))
                logger.info(f"Found video file: {video_path}")
                
                # Проверяем, существует ли файл
                if not os.path.exists(video_path):
                    raise FileNotFoundError(f"Видеофайл не существует: {video_path}")
                
                # Читаем байты файла
                with open(video_path, "rb") as f:
                    video_bytes = f.read()
                
                # Удаляем папку поста после чтения
                shutil.rmtree(post_dir, ignore_errors=True)
                logger.info(f"Removed post directory: {post_dir}")
                
                return video_bytes
        
        raise FileNotFoundError("Видеофайл не найден в папке поста")
            
    except instaloader.exceptions.LoginRequiredException:
        logger.error("Требуется авторизация для доступа к этому контенту")
        raise Exception("Требуется авторизация для доступа к этому контенту")
    except instaloader.exceptions.InvalidArgumentException:
        logger.error("Неверная ссылка или shortcode")
        raise Exception("Неверная ссылка или shortcode")
    except instaloader.exceptions.ConnectionException as e:
        logger.error(f"Ошибка соединения: {e}")
        raise Exception(f"Ошибка соединения: {e}")
    except FileNotFoundError as e:
        logger.error(f"Видеофайл не найден: {e}")
        raise Exception(f"Видеофайл не найден: {e}")
    except Exception as e:
        logger.error(f"Ошибка при скачивании видео: {e}")
        raise Exception(f"Ошибка при скачивании видео: {e}")