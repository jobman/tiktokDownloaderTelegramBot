import instaloader
import re
from urllib.parse import urlparse

def get_shortcode_from_url(url):
    """Извлекает shortcode из URL Instagram."""
    pattern = r'(?:/p/|/reel/)([A-Za-z0-9_-]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    else:
        raise ValueError("Невалидная ссылка на Instagram")

def download_instagram_video(url, username=None, password=None):
    """Скачивает видео из Instagram по URL."""
    try:
        # Инициализация Instaloader
        L = instaloader.Instaloader()

        # Авторизация, если предоставлены логин и пароль
        if username and password:
            L.login(username, password)
            print("Авторизация успешна")
        
        # Получение shortcode из URL
        shortcode = get_shortcode_from_url(url)
        
        # Загрузка поста
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        # Скачивание видео
        L.download_post(post, target="downloads")
        print(f"Видео успешно скачано в папку 'downloads'")
        
    except instaloader.exceptions.LoginRequiredException:
        print("Ошибка: Требуется авторизация для доступа к этому контенту")
    except instaloader.exceptions.InvalidArgumentException:
        print("Ошибка: Неверный shortcode или ссылка")
    except instaloader.exceptions.ConnectionException as e:
        print(f"Ошибка соединения: {e}")
    except Exception as e:
        print(f"Произошла ошибка: {e}")

if __name__ == "__main__":
    # Пример использования
    url = "https://www.instagram.com/reel/DGlkRFCtAml/?igsh=YnFpOWVndXh5czQ1"
    
    # Для приватных аккаунтов или контента, требующего авторизации
    # Раскомментируйте и укажите свои данные
    # username = "your_username"
    # password = "your_password"
    username = None
    password = None
    
    download_instagram_video(url, username, password)