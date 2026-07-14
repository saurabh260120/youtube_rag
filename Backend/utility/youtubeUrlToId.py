def urlToId(url):
    if "watch?v=" in url:
        video_id = url.split("v=")[-1]
        video_id = video_id.split("&")[0]
    elif "youtu.be/" in url:
        video_id = url.split("youtu.be/")[1]
    else:
        return None

    return video_id
