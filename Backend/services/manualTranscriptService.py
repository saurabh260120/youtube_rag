from services.transcriptService import parse_manual_transcript
from utility.youtubeUrlToId import urlToId


def process_manual_transcript(youtube_url: str, raw_transcript: str):
    """
    Process a manually pasted transcript from the user.

    Steps:
    1. Extract video_id from the URL.
    2. Parse the raw transcript text (supports timestamped and plain-text formats).
    3. Return the parsed/chunked transcript in the same format as get_trans().

    Returns:
        dict with:
            - "video_id": str
            - "transcript": list of {"text": str, "start": float, "end": float}
            - "message": str (success/error)
    """
    video_id = urlToId(youtube_url)
    if not video_id:
        return {
            "video_id": None,
            "transcript": None,
            "message": "Invalid YouTube URL. Could not extract video ID."
        }

    if not raw_transcript or not raw_transcript.strip():
        return {
            "video_id": video_id,
            "transcript": None,
            "message": "No transcript text provided."
        }

    parsed = parse_manual_transcript(raw_transcript)

    if not parsed or len(parsed) == 0:
        return {
            "video_id": video_id,
            "transcript": None,
            "message": "Could not parse any transcript segments from the provided text."
        }

    return {
        "video_id": video_id,
        "transcript": parsed,
        "message": f"Successfully parsed {len(parsed)} transcript segments."
    }