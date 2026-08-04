import os
import re

import yt_dlp

from settings import (
    YOUTUBE_COOKIES_FILE,
    YT_DLP_FRAGMENT_RETRIES,
    YT_DLP_RETRIES,
    YT_DLP_SOCKET_TIMEOUT,
)
from silent_logging import YT_DLP_LOGGER


def _get_ydl_options():
    options = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': '%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
        'logger': YT_DLP_LOGGER,
        'retries': YT_DLP_RETRIES,
        'fragment_retries': YT_DLP_FRAGMENT_RETRIES,
        'socket_timeout': YT_DLP_SOCKET_TIMEOUT,
    }

    if YOUTUBE_COOKIES_FILE:
        if not os.path.isfile(YOUTUBE_COOKIES_FILE):
            raise FileNotFoundError(
                f'YouTube cookies file not found: {YOUTUBE_COOKIES_FILE}'
            )
        options['cookiefile'] = YOUTUBE_COOKIES_FILE

    return options


def get_youtube_video(url):
    """Downloads a YouTube Shorts video and returns its bytes."""
    if not re.search(r"youtube\.com/shorts/", url):
        raise ValueError("The provided URL is not a YouTube Shorts link.")

    ydl_opts = _get_ydl_options()

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        video_id = info_dict.get("id", None)
        video_ext = info_dict.get("ext", None)
        filename = f"{video_id}.{video_ext}"

    with open(filename, 'rb') as f:
        video_bytes = f.read()
    
    os.remove(filename)

    return video_bytes
