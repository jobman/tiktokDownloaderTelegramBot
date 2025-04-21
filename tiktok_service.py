import pyktok as pyk
pyk.specify_browser('firefox')
import re
import requests
from bs4 import BeautifulSoup
import json
import browser_cookie3


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
                      timeout=20)
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
                      timeout=20)
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


def get_bytes(video_url):
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
                tt_video = requests.get(tt_video_url, allow_redirects=True, headers=headers, cookies=cookies)
                bytes_list.append(tt_video.content)
            return bytes_list
        else:
            try:
                tt_video_url = tt_json['ItemModule'][video_id]['video']['downloadAddr']
            except:
                tt_video_url = tt_json["__DEFAULT_SCOPE__"]['webapp.video-detail']['itemInfo']['itemStruct']['video']['downloadAddr']
            headers['referer'] = 'https://www.tiktok.com/'
            # include cookies with the video request
            tt_video = requests.get(tt_video_url, allow_redirects=True, headers=headers, cookies=cookies)
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
        tt_video = requests.get(tt_video_url, allow_redirects=True, headers=headers, cookies=cookies)
        return tt_video.content

if __name__ == "__main__":
    print(len(get_bytes("https://www.tiktok.com/@asya05283/video/7494392097303219511?is_from_webapp=1&sender_device=pc")))
