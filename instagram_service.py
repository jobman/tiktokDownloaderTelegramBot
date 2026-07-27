import instaloader
import re
import os
import shutil
import time
import yt_dlp

from settings import YT_DLP_FRAGMENT_RETRIES, YT_DLP_RETRIES, YT_DLP_SOCKET_TIMEOUT
from silent_logging import YT_DLP_LOGGER

def get_shortcode_from_url(url):
    """Извлекает shortcode из URL Instagram."""
    pattern = r'(?:/p/|/reel/)([A-Za-z0-9_-]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    else:
        raise ValueError("Невалидная ссылка на Instagram")

def get_instagram_video_by_yt_dlp(url):
    """Downloads an Instagram video using yt-dlp and returns its bytes."""
    output_filename = 'downloaded_instagram_video'
    ydl_opts = {
        'format': 'best',
        'outtmpl': output_filename,
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
        'logger': YT_DLP_LOGGER,
        'retries': YT_DLP_RETRIES,
        'fragment_retries': YT_DLP_FRAGMENT_RETRIES,
        'socket_timeout': YT_DLP_SOCKET_TIMEOUT,
    }

    downloaded_file = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
    except Exception:
        # The download might have failed, but the file might still be there.
        pass

    # Find the downloaded file, since we don't know the extension
    for f in os.listdir('.'):
        if f.startswith(output_filename):
            downloaded_file = f
            break

    if downloaded_file:
        with open(downloaded_file, 'rb') as f:
            video_bytes = f.read()
        
        os.remove(downloaded_file)
        return video_bytes
    else:
        raise Exception("Failed to download video with yt-dlp.")

def get_instagram_video(url, username=None, password=None):
    """Скачивает видео из Instagram и возвращает его байты."""
    try:
        # Инициализация Instaloader
        L = instaloader.Instaloader(
            download_pictures=False,
            download_comments=False,
            download_geotags=False,
            quiet=True,
        )
        L.context.error = lambda *args, **kwargs: None
        
        # Авторизация, если предоставлены логин и пароль
        if username and password:
            L.login(username, password)
        
        # Получение shortcode из URL
        shortcode = get_shortcode_from_url(url)
        
        # Абсолютный путь к папке с именем shortcode
        post_dir = os.path.normpath(os.path.join(os.getcwd(), shortcode))
        
        # Удаляем старую папку, если существует
        if os.path.exists(post_dir):
            shutil.rmtree(post_dir, ignore_errors=True)
        
        # Загрузка поста
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        # Проверка, является ли пост видео
        if not post.is_video:
            raise ValueError("Пост не содержит видео")
        
        # Скачиваем пост, передавая только shortcode как target
        L.download_post(post, target=shortcode)
        
        # Даём небольшую задержку, чтобы файл точно записался
        time.sleep(1)
        
        # Проверяем, существует ли папка
        if not os.path.exists(post_dir):
            raise FileNotFoundError(f"Папка поста не найдена: {post_dir}")
        
        # Логируем содержимое папки
        
        # Находим видеофайл в папке поста
        for file in os.listdir(post_dir):
            if file.endswith(".mp4"):
                video_path = os.path.normpath(os.path.join(post_dir, file))
                
                # Проверяем, существует ли файл
                if not os.path.exists(video_path):
                    raise FileNotFoundError(f"Видеофайл не существует: {video_path}")
                
                # Читаем байты файла
                with open(video_path, "rb") as f:
                    video_bytes = f.read()
                
                # Удаляем папку поста после чтения
                shutil.rmtree(post_dir, ignore_errors=True)
                
                return video_bytes
        
        raise FileNotFoundError("Видеофайл не найден в папке поста")
            
    except Exception:
        return get_instagram_video_by_yt_dlp(url)
