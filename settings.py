import os

from dotenv import find_dotenv, load_dotenv

_ENV_FILE = find_dotenv()
load_dotenv(_ENV_FILE)


def _get_youtube_cookies_file():
    configured = os.getenv('YOUTUBE_COOKIES_FILE')
    if configured:
        return configured

    # Also support the user's exported file beside the project or shared .env.
    directories = [os.path.dirname(os.path.abspath(__file__))]
    if _ENV_FILE:
        directories.append(os.path.dirname(os.path.realpath(_ENV_FILE)))
    for directory in directories:
        filename = os.path.join(directory, 'www.youtube.com_cookies.txt')
        if os.path.isfile(filename):
            return filename
    return None


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


YT_DLP_RETRIES = _get_int("MEDIA_DOWNLOAD_RETRIES", 5)
YT_DLP_FRAGMENT_RETRIES = _get_int("MEDIA_DOWNLOAD_FRAGMENT_RETRIES", YT_DLP_RETRIES)
YT_DLP_SOCKET_TIMEOUT = _get_int("MEDIA_DOWNLOAD_SOCKET_TIMEOUT", 60)
YT_DLP_DOWNLOAD_ATTEMPTS = _get_int("MEDIA_YT_DLP_DOWNLOAD_ATTEMPTS", 8)
YOUTUBE_COOKIES_FILE = _get_youtube_cookies_file()
YOUTUBE_PYTUBEFIX_ATTEMPTS = _get_int("YOUTUBE_PYTUBEFIX_ATTEMPTS", 8)
TELEGRAM_VIDEO_MAX_BYTES = _get_int("TELEGRAM_VIDEO_MAX_BYTES", 48_000_000)
VIDEO_COMPRESSION_TIMEOUT = _get_int("VIDEO_COMPRESSION_TIMEOUT", 900)

REQUEST_CONNECT_TIMEOUT = _get_int("MEDIA_REQUEST_CONNECT_TIMEOUT", 15)
REQUEST_READ_TIMEOUT = _get_int("MEDIA_REQUEST_READ_TIMEOUT", 60)
REQUEST_RETRIES = _get_int("MEDIA_REQUEST_RETRIES", 5)

BLOCKING_RETRIES = _get_int("MEDIA_BLOCKING_RETRIES", 4)
BLOCKING_RETRY_DELAY = _get_int("MEDIA_BLOCKING_RETRY_DELAY", 2)
