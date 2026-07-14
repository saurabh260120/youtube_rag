from yt_dlp import YoutubeDL

def get_video_duration(video_url):
    ydl_opts = {
        "quiet": True,
        "skip_download": True
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)

    return info["duration"]  # seconds