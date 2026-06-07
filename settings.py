import os

from dotenv import load_dotenv

load_dotenv()


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
YT_DLP_DOWNLOAD_ATTEMPTS = _get_int("MEDIA_YT_DLP_DOWNLOAD_ATTEMPTS", 3)

REQUEST_CONNECT_TIMEOUT = _get_int("MEDIA_REQUEST_CONNECT_TIMEOUT", 15)
REQUEST_READ_TIMEOUT = _get_int("MEDIA_REQUEST_READ_TIMEOUT", 60)
REQUEST_RETRIES = _get_int("MEDIA_REQUEST_RETRIES", 5)

BLOCKING_RETRIES = _get_int("MEDIA_BLOCKING_RETRIES", 4)
BLOCKING_RETRY_DELAY = _get_int("MEDIA_BLOCKING_RETRY_DELAY", 2)
