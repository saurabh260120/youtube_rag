from youtube_transcript_api import YouTubeTranscriptApi
from supadata import Supadata
from utility.logger import log

ytt_api = YouTubeTranscriptApi()

# Initialize Supadata client for fallback
from dotenv import load_dotenv
import os
load_dotenv()
SUPA_DATA_API_KEY = os.getenv("SUPA_DATA_API_KEY")
supadata_client = Supadata(api_key=SUPA_DATA_API_KEY)

import re


def merge_into_sentences_old(snippets):
    sentences = []

    current_text = []
    current_start = None
    current_end = None

    for snippet in snippets:
        text = snippet.text.strip()

        if current_start is None:
            current_start = snippet.start

        current_text.append(text)
        current_end = snippet.start + snippet.duration

        # Check if the snippet ends with sentence-ending punctuation
        if re.search(r"[.!?]$", text):
            sentences.append({
                "text": " ".join(current_text),
                "start": current_start,
                "end": current_end
            })

            current_text = []
            current_start = None
            current_end = None

    # Handle any remaining text
    if current_text:
        sentences.append({
            "text": " ".join(current_text),
            "start": current_start,
            "end": current_end
        })

    return sentences


def merge_into_sentences(snippets, max_chars=800):
    chunks = []

    current_text = []
    current_start = None
    current_end = None
    current_length = 0

    for snippet in snippets:
        text = snippet.text.strip()

        if current_start is None:
            current_start = snippet.start

        # If adding this snippet would exceed the limit,
        # flush the current chunk first.
        if current_length + len(text) > max_chars and current_text:
            chunks.append({
                "text": " ".join(current_text),
                "start": current_start,
                "end": current_end,
            })

            current_text = []
            current_start = snippet.start
            current_length = 0

        current_text.append(text)
        current_length += len(text) + 1
        current_end = snippet.start + snippet.duration

    if current_text:
        chunks.append({
            "text": " ".join(current_text),
            "start": current_start,
            "end": current_end,
        })

    return chunks


def get_best_transcript(video_id: str):
    try:
        transcript_list = ytt_api.list(video_id)

        # 1. English manual
        try:
            transcript = transcript_list.find_manually_created_transcript(["en"])
            return transcript.fetch()
        except Exception as e:
            log(f"get_best_transcript: English manual transcript not found for video {video_id}: {e}")
            pass

        # 2. English generated
        try:
            transcript = transcript_list.find_generated_transcript(["en"])
            return transcript.fetch()
        except Exception as e:
            log(f"get_best_transcript: English generated transcript not found for video {video_id}: {e}")
            pass

        # 3. Any manual transcript
        for t in transcript_list:
            if not t.is_generated:
                return t.fetch()

        # 4. Any generated transcript
        for t in transcript_list:
            if t.is_generated:
                return t.fetch()

        return None
    except Exception as e:
        log(f"get_best_transcript: youtube-transcript-api failed for video {video_id}: {e}")
        return None


def _supadata_snippets_to_fetch_format(snippets_data):
    """Convert Supadata transcript segments to match youtube_transcript_api's snippet format."""
    class Snippet:
        def __init__(self, text, start, duration):
            self.text = text
            self.start = start
            self.duration = duration

    def _get_snippet_val(seg, attr_dict_name, fallback):
        """Extract value from dict-like or object-like segment safely."""
        if isinstance(seg, dict):
            return seg.get(attr_dict_name, fallback)
        return getattr(seg, attr_dict_name, fallback)

    return [Snippet(
        text=_get_snippet_val(seg, "text", ""),
        start=_get_snippet_val(seg, "offset", 0),
        duration=_get_snippet_val(seg, "duration", 0)
    ) for seg in snippets_data]


def get_transcript_from_supadata(video_id: str):
    """Fallback: fetch transcript using Supadata API."""
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        log(f"get_transcript_from_supadata: Fetching transcript from Supadata for video {video_id}")
        result = supadata_client.transcript(url=url)

        # The result may be a dict (JSON response) or an object with attributes.
        if hasattr(result, "content"):
            snippets_data = result.content
        elif isinstance(result, dict):
            snippets_data = result.get("content", result)
        else:
            log(f"get_transcript_from_supadata: Unexpected Supadata response type: {type(result)} for video {video_id}")
            return None

        # If Supadata returned a list directly (array of segments)
        if isinstance(snippets_data, list) and len(snippets_data) > 0:
            log(f"get_transcript_from_supadata: Successfully fetched {len(snippets_data)} segments from Supadata for video {video_id}")
            return _supadata_snippets_to_fetch_format(snippets_data)

        log(f"get_transcript_from_supadata: No transcript content found from Supadata for video {video_id}")
        return None

    except Exception as e:
        log(f"get_transcript_from_supadata: Supadata fallback failed for video {video_id}: {e}")
        return None


def get_trans(video_id: str):
    log(f"get_trans: Attempting to fetch transcript for video {video_id}")
    transcript = get_best_transcript(video_id)

    if transcript is not None:
        log(f"get_trans: Fetched transcript from youtube-transcript-api for video {video_id}")
        return merge_into_sentences(transcript.snippets)

    # Fallback to Supadata if youtube-transcript-api returned nothing
    log(f"get_trans: youtube-transcript-api returned no transcript, trying Supadata fallback for video {video_id}")
    fallback_transcript = get_transcript_from_supadata(video_id)
    if fallback_transcript is not None:
        log(f"get_trans: Fetched transcript from Supadata for video {video_id}")
        return merge_into_sentences(fallback_transcript)

    log(f"get_trans: No transcript found for video {video_id} from any source")
    return None


# ---------------------------------------------------------------------------
# Manual transcript parsing (fallback from user-pasted content)
# ---------------------------------------------------------------------------

def _parse_timestamp(ts_str: str) -> float:
    """
    Convert a timestamp string like '00:00:00' or '00:02' to total seconds (float).
    Supports both HH:MM:SS and MM:SS formats.
    """
    parts = ts_str.strip().split(":")
    if len(parts) == 3:
        # HH:MM:SS
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    elif len(parts) == 2:
        # MM:SS
        return int(parts[0]) * 60 + float(parts[1])
    else:
        # just a number -> seconds
        return float(parts[0])


def parse_manual_transcript(raw_text: str):
    """
    Parse a user-pasted transcript from https://youtubetotranscript.com/.

    Supports two formats:

    Format 1 – Timestamped lines (each line starts with a timestamp):
        00:00:00 आज से 2 साल पहले जिन शेयरों को मैंने
        00:00:02 बेचा था उनकी कीमत ₹200 करोड़ थी।
        ...

    Format 2 – Plain text (no timestamps, just running text):
        आज से 2 साल पहले जिन शेयरों को मैंने बेचा था उनकी कीमत ...

    Returns a list of dicts in the same format as merge_into_sentences():
        [{"text": "...", "start": <seconds>, "end": <seconds>}, ...]

    For plain-text input, each sentence or sentence-like segment gets approximate
    start/end timestamps of 0 / total_duration_estimate.
    """
    lines = raw_text.strip().splitlines()
    if not lines:
        return []

    # Detect if the first few non-empty lines have timestamps (MM:SS or HH:MM:SS)
    timestamp_pattern = re.compile(r"^\d{1,2}:\d{2}(?::\d{2})?\s+")

    has_timestamps = False
    for line in lines:
        stripped = line.strip()
        if stripped and timestamp_pattern.match(stripped):
            has_timestamps = True
            break

    if has_timestamps:
        return _parse_timestamped_transcript(lines, timestamp_pattern)
    else:
        return _parse_plain_text_transcript(raw_text)


def _parse_timestamped_transcript(lines, timestamp_pattern):
    """
    Parse timestamped lines into chunked transcript segments.
    Each line like '00:00:00 text text' becomes a snippet.
    Then chunks them using merge_into_sentences-like logic.
    """
    snippets = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        match = timestamp_pattern.match(stripped)
        if not match:
            continue

        ts_str = match.group().strip()
        text = stripped[match.end():].strip()

        if not text:
            continue

        start_sec = _parse_timestamp(ts_str)

        # Estimate duration: assume next timestamp - current, or default 4 seconds
        # We'll set a default short duration; chunks will merge them anyway.
        # For the snippet-based chunking below, we need start and duration.
        snippets.append({
            "text": text,
            "start": start_sec,
            "duration": 4.0,  # default 4s per line; will be overridden in chunking
        })

    # Now convert snippets into chunks using our chunking logic
    return _chunk_manual_snippets(snippets)


def _parse_plain_text_transcript(raw_text):
    """
    Parse plain text (no timestamps) into chunked segments.
    Splits on sentence boundaries first, then chunks into ~800 char blocks.
    """
    # Split into sentences by sentence-ending punctuation
    sentences = re.split(r"(?<=[.!?])\s+", raw_text.strip())

    chunks = []
    current_text = []
    current_length = 0
    max_chars = 800

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if current_length + len(sentence) > max_chars and current_text:
            chunks.append({
                "text": " ".join(current_text),
                "start": 0,
                "end": 0,
            })
            current_text = []
            current_length = 0

        current_text.append(sentence)
        current_length += len(sentence) + 1

    if current_text:
        chunks.append({
            "text": " ".join(current_text),
            "start": 0,
            "end": 0,
        })

    return chunks


def _chunk_manual_snippets(snippets, max_chars=800):
    """
    Chunk manual transcript snippets (dicts with text/start/duration)
    into larger segments, similar to merge_into_sentences logic.
    """
    chunks = []
    current_text = []
    current_start = None
    current_end = None
    current_length = 0

    for snippet in snippets:
        text = snippet["text"]

        if current_start is None:
            current_start = snippet["start"]

        if current_length + len(text) > max_chars and current_text:
            chunks.append({
                "text": " ".join(current_text),
                "start": current_start,
                "end": current_end or (current_start + 4.0),
            })
            current_text = []
            current_start = snippet["start"]
            current_length = 0

        current_text.append(text)
        current_length += len(text) + 1
        current_end = snippet["start"] + snippet.get("duration", 4.0)

    if current_text:
        chunks.append({
            "text": " ".join(current_text),
            "start": current_start or 0,
            "end": current_end or 0,
        })

    return chunks