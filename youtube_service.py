import yt_dlp
import re

def get_youtube_video(url):
    """Downloads a YouTube Shorts video and returns its bytes."""
    if not re.search(r"youtube\.com/shorts/", url):
        raise ValueError("The provided URL is not a YouTube Shorts link.")

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': '%(id)s.%(ext)s',
        'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        video_id = info_dict.get("id", None)
        video_ext = info_dict.get("ext", None)
        filename = f"{video_id}.{video_ext}"

    with open(filename, 'rb') as f:
        video_bytes = f.read()
    
    import os
    os.remove(filename)

    return video_bytes
