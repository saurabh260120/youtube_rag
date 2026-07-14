from youtube_transcript_api import YouTubeTranscriptApi

ytt_api = YouTubeTranscriptApi()

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

def merge_into_sentences(snippets,max_chars=800):
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
    transcript_list = ytt_api.list(video_id)

    # 1. English manual
    try:
        transcript = transcript_list.find_manually_created_transcript(["en"])
        return transcript.fetch()
    except Exception as e:
        print(f"English manual transcript not found for video {video_id}: {e}")
        pass

    # 2. English generated
    try:
        transcript = transcript_list.find_generated_transcript(["en"])
        return transcript.fetch()
    except Exception as e:
        print(f"English manual generated not found for video {video_id}: {e}")
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

def get_trans(video_id: str):
    transcript = get_best_transcript(video_id)
    if transcript is not None:
        print(f"Fetched transcript for video {video_id}")
        return merge_into_sentences(transcript.snippets)
    else :
        print(f"no transcript found for the video {video_id}")
        return None

def get_raw_transcript(video_id: str):
    try:
        transcript = ytt_api.fetch(video_id)
        print(f"Fetched raw transcript for video {video_id}")
        return transcript.snippets
    except Exception as e:
        print(f"Error occurred while fetching raw transcript for video {video_id}: {e}")
        return None