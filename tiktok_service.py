import re
import requests
from bs4 import BeautifulSoup
import json
import browser_cookie3
import yt_dlp
import os
import time
from urllib.parse import urlsplit, urlunsplit
from requests.exceptions import Timeout as RequestsTimeout, RequestException

from settings import (
    REQUEST_CONNECT_TIMEOUT,
    REQUEST_READ_TIMEOUT,
    REQUEST_RETRIES,
    YT_DLP_DOWNLOAD_ATTEMPTS,
    YT_DLP_FRAGMENT_RETRIES,
    YT_DLP_RETRIES,
    YT_DLP_SOCKET_TIMEOUT,
)
from silent_logging import YT_DLP_LOGGER


url_regex = '(?<=\.com/)(.+?)(?=\?|$)'
headers = {'Accept-Encoding': 'gzip, deflate, sdch',
           'Accept-Language': 'en-US,en;q=0.8',
           'Upgrade-Insecure-Requests': '1',
           'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
           'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
           'Cache-Control': 'max-age=0',
           'Connection': 'keep-alive'}

def get_tiktok_json(video_url,browser_name=None):
    if 'cookies' not in globals() and browser_name is None:
        raise ValueError('No browser defined for cookie extraction. We strongly recommend you run \'specify_browser\', which takes as its sole argument a string representing a browser installed on your system, e.g. "chrome," "firefox," "edge," etc.')
    global cookies
    if browser_name is not None:
        cookies = getattr(browser_cookie3,browser_name)(domain_name='.tiktok.com')
    tt = requests.get(video_url,
                      headers=headers,
                      cookies=cookies,
                      timeout=(REQUEST_CONNECT_TIMEOUT, REQUEST_READ_TIMEOUT))
    # retain any new cookies that got set in this request
    cookies = tt.cookies
    soup = BeautifulSoup(tt.text, "html.parser")
    tt_script = soup.find('script', attrs={'id':"SIGI_STATE"})
    try:
        tt_json = json.loads(tt_script.string)
    except AttributeError:
        return
    return tt_json

def alt_get_tiktok_json(video_url,browser_name=None):
    if 'cookies' not in globals() and browser_name is None:
        raise ValueError('No browser defined for cookie extraction. We strongly recommend you run \'specify_browser\', which takes as its sole argument a string representing a browser installed on your system, e.g. "chrome," "firefox," "edge," etc.')
    global cookies
    if browser_name is not None:
        cookies = getattr(browser_cookie3,browser_name)(domain_name='.tiktok.com')
    tt = requests.get(video_url,
                      headers=headers,
                      cookies=cookies,
                      timeout=(REQUEST_CONNECT_TIMEOUT, REQUEST_READ_TIMEOUT))
    # retain any new cookies that got set in this request
    cookies = tt.cookies
    soup = BeautifulSoup(tt.text, "html.parser")
    tt_script = soup.find('script', attrs={'id':"__UNIVERSAL_DATA_FOR_REHYDRATION__"})
    try:
        tt_json = json.loads(tt_script.string)
    except AttributeError:
        return
    return tt_json

def _find_downloaded_file(output_filename):
    for filename in os.listdir('.'):
        if filename.startswith(output_filename):
            return filename
    return None


def _remove_downloaded_files(output_filename):
    for filename in os.listdir('.'):
        if filename.startswith(output_filename):
            try:
                os.remove(filename)
            except OSError:
                pass


def _resolve_tiktok_url(url):
    """Resolve short TikTok links before extraction to avoid repeated redirects."""
    if not re.match(r'https?://(?:vm|vt)\.tiktok\.com/', url):
        return url

    try:
        with requests.get(
            url,
            allow_redirects=True,
            headers=headers,
            stream=True,
            timeout=(REQUEST_CONNECT_TIMEOUT, REQUEST_READ_TIMEOUT),
        ) as response:
            response.raise_for_status()
            resolved = urlsplit(response.url)
            return urlunsplit((resolved.scheme, resolved.netloc, resolved.path, '', ''))
    except RequestException:
        return url


def _get_tiktok_video_from_embed(url):
    """Download a TikTok video through its public embed metadata."""
    video_id_match = re.search(r'/video/(\d+)', url)
    if not video_id_match:
        raise ValueError('Unable to extract TikTok video ID')

    video_id = video_id_match.group(1)
    embed_url = f'https://www.tiktok.com/embed/v2/{video_id}'
    response = _request_with_retry(embed_url, headers, {})
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    state_script = soup.find('script', attrs={'id': '__FRONTITY_CONNECT_STATE__'})
    if state_script is None:
        raise ValueError('Unable to extract TikTok embed state')

    state = json.loads(state_script.get_text())
    route_values = state.get('source', {}).get('data', {}).values()
    item_info = next(
        (
            route.get('videoData', {}).get('itemInfos')
            for route in route_values
            if isinstance(route, dict) and route.get('videoData', {}).get('itemInfos')
        ),
        None,
    )
    video_urls = item_info.get('video', {}).get('urls', []) if item_info else []
    if not video_urls:
        raise ValueError('Unable to extract TikTok embed video URL')

    video_headers = {**headers, 'Referer': embed_url}
    last_error = None
    for video_url in video_urls:
        try:
            video_response = _request_with_retry(video_url, video_headers, {})
            video_response.raise_for_status()
            if video_response.content:
                return video_response.content
        except RequestException as exc:
            last_error = exc

    if last_error:
        raise last_error
    raise ValueError('TikTok embed returned an empty video')


def get_tiktok_video_by_yt_dlp(url):
    """Download a TikTok video, with yt-dlp as a fallback."""
    output_filename = 'downloaded_tiktok_video'
    attempts = max(1, YT_DLP_DOWNLOAD_ATTEMPTS)
    resolved_url = _resolve_tiktok_url(url)
    try:
        return _get_tiktok_video_from_embed(resolved_url)
    except Exception:
        pass

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

    last_error = None
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for attempt in range(attempts):
            _remove_downloaded_files(output_filename)
            downloaded_file = None
            try:
                ydl.extract_info(resolved_url, download=True)
            except Exception as exc:
                last_error = exc

            # Find the downloaded file, since we don't know the extension.
            downloaded_file = _find_downloaded_file(output_filename)

            if downloaded_file:
                with open(downloaded_file, 'rb') as f:
                    video_bytes = f.read()

                os.remove(downloaded_file)
                return video_bytes

            if attempt < attempts - 1:
                time.sleep(min(1.5 ** attempt, 8))

    if last_error:
        raise Exception(f"Failed to download video with yt-dlp after {attempts} attempts: {last_error}")
    raise Exception(f"Failed to download video with yt-dlp after {attempts} attempts.")

def _request_with_retry(url, request_headers, request_cookies, retries=REQUEST_RETRIES, backoff=1.5):
    last_exc = None
    for attempt in range(retries):
        try:
            return requests.get(
                url,
                allow_redirects=True,
                headers=request_headers,
                cookies=request_cookies,
                timeout=(REQUEST_CONNECT_TIMEOUT, REQUEST_READ_TIMEOUT),
            )
        except (RequestsTimeout, RequestException) as exc:
            last_exc = exc
            if attempt < retries - 1:
                time.sleep(backoff ** attempt)
    raise last_exc

def get_bytes(video_url):
    try:
        browser_name="firefox"
        if 'cookies' not in globals() and browser_name is None:
            raise ValueError('No browser defined for cookie extraction. We strongly recommend you run \'specify_browser\', which takes as its sole argument a string representing a browser installed on your system, e.g. "chrome," "firefox," "edge," etc.')

        tt_json = get_tiktok_json(video_url,browser_name)

        if tt_json is not None:
            video_id = list(tt_json['ItemModule'].keys())[0]
            if 'imagePost' in tt_json['ItemModule'][video_id]:
                bytes_list = []
                for slide in tt_json['ItemModule'][video_id]['imagePost']['images']:
                    tt_video_url = slide['imageURL']['urlList'][0]
                    headers['referer'] = 'https://www.tiktok.com/'
                    # include cookies with the video request
                    tt_video = _request_with_retry(tt_video_url, headers, cookies)
                    bytes_list.append(tt_video.content)
                return bytes_list
            else:
                try:
                    tt_video_url = tt_json['ItemModule'][video_id]['video']['downloadAddr']
                except:
                    tt_video_url = tt_json["__DEFAULT_SCOPE__"]['webapp.video-detail']['itemInfo']['itemStruct']['video']['downloadAddr']
                headers['referer'] = 'https://www.tiktok.com/'
                # include cookies with the video request
                tt_video = _request_with_retry(tt_video_url, headers, cookies)
            return tt_video.content

        else:
            tt_json = alt_get_tiktok_json(video_url,browser_name)

            try:
                tt_video_url = tt_json["__DEFAULT_SCOPE__"]['webapp.video-detail']['itemInfo']['itemStruct']['video']['playAddr']
                if tt_video_url == '':
                    raise
            except:
                tt_video_url = tt_json["__DEFAULT_SCOPE__"]['webapp.video-detail']['itemInfo']['itemStruct']['video']['downloadAddr']
            headers['referer'] = 'https://www.tiktok.com/'
            # include cookies with the video request
            tt_video = _request_with_retry(tt_video_url, headers, cookies)
            return tt_video.content
    except Exception:
        return get_tiktok_video_by_yt_dlp(video_url)
