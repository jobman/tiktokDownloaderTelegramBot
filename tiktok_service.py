import pyktok as pyk
pyk.specify_browser('firefox')
import re
import requests
from bs4 import BeautifulSoup
import json
import browser_cookie3
import yt_dlp
import os
import time
from requests.exceptions import Timeout as RequestsTimeout, RequestException

from settings import (
    REQUEST_CONNECT_TIMEOUT,
    REQUEST_READ_TIMEOUT,
    REQUEST_RETRIES,
    YT_DLP_FRAGMENT_RETRIES,
    YT_DLP_RETRIES,
    YT_DLP_SOCKET_TIMEOUT,
)


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
        print("The function encountered a downstream error and did not deliver any data, which happens periodically for various reasons. Please try again later.")
        return
    return tt_json

def get_tiktok_video_by_yt_dlp(url):
    """Downloads a TikTok video using yt-dlp and returns its bytes."""
    output_filename = 'downloaded_tiktok_video'
    ydl_opts = {
        'format': 'best',
        'outtmpl': output_filename,
        'quiet': True,
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

if __name__ == "__main__":
    print(len(get_bytes("https://vm.tiktok.com/ZMBWpLNH2/")))
