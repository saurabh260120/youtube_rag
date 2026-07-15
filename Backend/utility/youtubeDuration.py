from googleapiclient.discovery import build
from urllib.parse import urlparse, parse_qs
import re
import os

from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("YOUTUBE_DATA_API")


def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats."""

    # https://youtu.be/VIDEO_ID
    if "youtu.be" in url:
        return url.split("/")[-1].split("?")[0]

    # https://www.youtube.com/watch?v=VIDEO_ID
    parsed = urlparse(url)
    if parsed.hostname in (
        "www.youtube.com",
        "youtube.com",
        "m.youtube.com",
    ):
        return parse_qs(parsed.query).get("v", [None])[0]

    # Already a video ID
    if re.match(r"^[A-Za-z0-9_-]{11}$", url):
        return url

    raise ValueError("Invalid YouTube URL")


def parse_iso8601_duration(duration: str) -> int:
    """
    Converts ISO 8601 duration (e.g. PT1H2M30S) to seconds.
    """
    pattern = re.compile(
        r"PT"
        r"(?:(\d+)H)?"
        r"(?:(\d+)M)?"
        r"(?:(\d+)S)?"
    )

    match = pattern.match(duration)

    if not match:
        return 0

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)

    return hours * 3600 + minutes * 60 + seconds


def get_video_duration(video_url: str) -> int:
    youtube = build("youtube", "v3", developerKey=API_KEY)

    video_id = extract_video_id(video_url)

    request = youtube.videos().list(
        part="contentDetails",
        id=video_id
    )

    response = request.execute()

    if not response["items"]:
        raise ValueError("Video not found")

    duration = response["items"][0]["contentDetails"]["duration"]

    return parse_iso8601_duration(duration)