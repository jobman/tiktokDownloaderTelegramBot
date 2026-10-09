from io import BytesIO
import os
import re
import tempfile
import time

import nodejs_wheel
import yt_dlp
from pytubefix import YouTube

from settings import (
    YOUTUBE_COOKIES_FILE,
    YOUTUBE_PYTUBEFIX_ATTEMPTS,
    YT_DLP_FRAGMENT_RETRIES,
    YT_DLP_RETRIES,
    YT_DLP_SOCKET_TIMEOUT,
)
from silent_logging import YT_DLP_LOGGER


def _get_node_runtime_options():
    # The system Node may be too old for yt-dlp's YouTube challenge solver.
    root = os.path.dirname(nodejs_wheel.__file__)
    executable = (
        os.path.join(root, 'node.exe')
        if os.name == 'nt'
        else os.path.join(root, 'bin', 'node')
    )
    if os.path.isfile(executable):
        return {'path': executable}
    return {}


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
        'js_runtimes': {'node': _get_node_runtime_options()},
    }

    if YOUTUBE_COOKIES_FILE:
        if not os.path.isfile(YOUTUBE_COOKIES_FILE):
            raise FileNotFoundError(
                f'YouTube cookies file not found: {YOUTUBE_COOKIES_FILE}'
            )
        options['cookiefile'] = YOUTUBE_COOKIES_FILE

    return options


PYTUBEFIX_CLIENTS = ('MWEB', 'ANDROID_VR')
YOUTUBE_HLS_FORMAT = (
    'bv[protocol^=m3u8][vcodec^=avc1][height<=1280]+ba[protocol^=m3u8]'
    '/b[protocol^=m3u8][height<=1280]'
)


def _download_with_pytubefix_client(url, client):
    stream = YouTube(url, client=client).streams.get_highest_resolution()
    if stream is None:
        raise RuntimeError('pytubefix did not find a downloadable video stream')

    buffer = BytesIO()
    stream.stream_to_buffer(buffer)
    return buffer.getvalue()


def _get_youtube_video_with_pytubefix(url):
    attempts = max(1, YOUTUBE_PYTUBEFIX_ATTEMPTS)
    last_error = None
    for attempt in range(attempts):
        client = PYTUBEFIX_CLIENTS[attempt % len(PYTUBEFIX_CLIENTS)]
        try:
            return _download_with_pytubefix_client(url, client)
        except Exception as exc:
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(min(1.5 ** attempt, 5))

    raise RuntimeError(
        f'pytubefix failed after {attempts} attempts: {last_error}'
    ) from last_error


def _download_with_yt_dlp_options(url, options):
    # Isolate partial files and simultaneous requests, including HLS fallback.
    with tempfile.TemporaryDirectory(prefix='youtube-') as directory:
        options = dict(options, outtmpl=os.path.join(directory, '%(id)s.%(ext)s'))
        with yt_dlp.YoutubeDL(options) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info_dict)
        with open(filename, 'rb') as video:
            return video.read()


def _get_youtube_video_with_yt_dlp(url):
    options = _get_ydl_options()
    try:
        return _download_with_yt_dlp_options(url, options)
    except yt_dlp.utils.DownloadError as exc:
        if not re.search(r'\b403\b', str(exc)):
            raise

    # HLS can remain available when direct Google Video URLs reject playback.
    hls_options = dict(
        options,
        format=YOUTUBE_HLS_FORMAT,
        merge_output_format='mp4',
        skip_unavailable_fragments=False,
    )
    return _download_with_yt_dlp_options(url, hls_options)


def get_youtube_video(url):
    """Downloads a YouTube Shorts video and returns its bytes."""
    if not re.search(r"youtube\.com/shorts/", url):
        raise ValueError("The provided URL is not a YouTube Shorts link.")

    try:
        return _get_youtube_video_with_pytubefix(url)
    except Exception as pytubefix_error:
        try:
            return _get_youtube_video_with_yt_dlp(url)
        except Exception as yt_dlp_error:
            raise RuntimeError(
                'Unable to download YouTube video with pytubefix or yt-dlp: '
                f'{pytubefix_error}; {yt_dlp_error}'
            ) from yt_dlp_error
