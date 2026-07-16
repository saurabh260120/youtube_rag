import asyncio
import json
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from aio_pika import Message
from dotenv import load_dotenv

from utility.youtubeUrlToId import urlToId
from utility.youtubeDuration import get_video_duration
from utility.logger import log

from Model.quizRequestModel import QuizRequestItem
from Model.userQueryModel import userQueryItem
from Model.manualTranscriptModel import ManualTranscriptRequest

from services.quizGenerationService import generateQuiz
from services.transcriptConsumer import start_consumer
from services.answerQueryService import answerQuery
from services.manualTranscriptService import process_manual_transcript
from rabbitMQ import rabbitMq

load_dotenv()

QUEUE_NAME = "quiz_generation_queue"
PINECODE_EMBEDDING_QUEUE_NAME = "pinecode-embeddingqueue"

app = FastAPI()

allow_origins = os.getenv("ALLOWED_CORS_ORIGINS", "").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    log("Health check: root endpoint called")
    return {"message": "Hello World, I am Up and running"}


@app.get("/health")
async def health():
    log("Health check: /health endpoint called")
    return {"status": "healthy"}


@app.on_event("startup")
async def startup_event():
    log("Application starting, starting RabbitMQ consumers...")
    asyncio.create_task(start_consumer())


@app.post("/generateQuiz")
async def generate_quiz(quiz_request: QuizRequestItem):
    log(f"POST /generateQuiz called for URL: {quiz_request.youtubeUrl}")
    duration = get_video_duration(quiz_request.youtubeUrl)
    log(f"Video duration: {duration}s for URL: {quiz_request.youtubeUrl}")
    if duration > 1800:
        log(f"Video too long ({duration}s > 1800s), rejecting URL: {quiz_request.youtubeUrl}")
        return {"message": "This application currently supports videos up to half hour long. Longer videos require significantly more llm calls so they aren't supported on the current free tier."}
    return await generateQuiz(quiz_request.youtubeUrl)


# feature 2
# user query a youtube video after pasting a link
@app.post("/userQuery")
async def user_query(user_query: userQueryItem):
    log(f"POST /userQuery called for URL: {user_query.youtubeUrl}")
    duration = get_video_duration(user_query.youtubeUrl)
    log(f"Video duration: {duration}s for URL: {user_query.youtubeUrl}")
    if duration > 3600:
        log(f"Video too long ({duration}s > 3600s), rejecting URL: {user_query.youtubeUrl}")
        return {"message": "This application currently supports videos up to 1 hour long. Longer videos require significantly more embedding requests, so they aren't supported on the current free tier."}
    video_id = urlToId(user_query.youtubeUrl)
    log(f"Extracted video_id: {video_id} from URL: {user_query.youtubeUrl}")
    return await answerQuery(video_id, user_query.user_question)


# ---------------------------------------------------------------------------
# Manual transcript fallback endpoint
# ---------------------------------------------------------------------------
@app.post("/submitManualTranscript")
async def submit_manual_transcript(request: ManualTranscriptRequest):
    """
    Accept a manually pasted transcript from the user (from youtubetotranscript.com).
    Parses it, then pushes it to the quiz generation queue and/or embedding queue
    just like an auto-fetched transcript would be handled.
    """
    log(f"POST /submitManualTranscript called for URL: {request.youtubeUrl}")
    video_id = urlToId(request.youtubeUrl)
    if not video_id:
        log(f"Failed to extract video ID from URL: {request.youtubeUrl}")
        return {"message": "Invalid YouTube URL. Could not extract video ID."}

    log(f"Processing manual transcript for video {video_id}")

    # Parse the manual transcript
    result = process_manual_transcript(request.youtubeUrl, request.transcript)

    if result["transcript"] is None:
        log(f"Manual transcript parsing failed for video {video_id}: {result['message']}")
        return {"message": result["message"]}

    parsed_transcript = result["transcript"]
    log(f"Manual transcript parsed successfully: {len(parsed_transcript)} segments for video {video_id}")

    # --- Push to quiz generation queue ---
    quiz_payload = {
        "video_id": video_id,
        "video_url": request.youtubeUrl,
        "transcript": parsed_transcript
    }

    rabbit_channel = await rabbitMq.get_channel()
    quiz_queue = await rabbit_channel.declare_queue(QUEUE_NAME, durable=True)

    await rabbit_channel.default_exchange.publish(
        Message(
            body=json.dumps(quiz_payload).encode(),
            delivery_mode=2,
        ),
        routing_key=quiz_queue.name
    )
    log(f"Manual transcript pushed to quiz generation queue for video {video_id}")

    # --- Also push to embedding generation queue with the parsed transcript ---
    # We include the transcript so the embedding consumer doesn't need to re-fetch it
    embedding_payload = {
        "video_id": video_id,
        "manual_transcript": parsed_transcript,  # pre-parsed transcript for embedding
    }

    embedding_queue = await rabbit_channel.declare_queue(
        PINECODE_EMBEDDING_QUEUE_NAME,
        durable=True
    )

    await rabbit_channel.default_exchange.publish(
        Message(
            body=json.dumps(embedding_payload).encode(),
            delivery_mode=2,
        ),
        routing_key=embedding_queue.name
    )
    log(f"Manual transcript pushed to embedding queue for video {video_id}")

    return {
        "message": "Manual transcript submitted successfully. Quiz generation and embedding generation have been queued.",
        "video_id": video_id,
        "segments_parsed": len(parsed_transcript),
    }