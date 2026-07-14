
from email import utils

from db.connection import client
collection = client["quizDB"]["quizCollection"]

from services.transcriptService import get_trans
from utility.youtubeUrlToId import urlToId

from llm import llm

import json
from aio_pika import Message
from rabbitMQ import rabbitMq

QUEUE_NAME = "quiz_generation_queue"

def sanitize_quiz_doc(doc: dict) -> dict:
    if doc is None:
        return doc
    sanitized = doc.copy()
    if "_id" in sanitized:
        sanitized["id"] = str(sanitized.pop("_id"))
    return sanitized




async def generateQuiz(yt_url: str):

    video_id = urlToId(yt_url)
    # first check if the quiz already exists in the database
    existing_quiz = collection.find_one({"video_id": video_id})

    if existing_quiz:
        if existing_quiz.get("is_educational") is False:
            return {"message": "The video content is not educational. Quiz generation aborted."}
        return {
            "message": "Quiz already exists for the given video ID",
            "quiz": sanitize_quiz_doc(existing_quiz),
        }

    transcript = get_trans(video_id)
    if(transcript is None):
        return {"message": "Transacript not found for the given video ID"}
    
    print("Transcript pushing to RabbitMQ queue for processing...")
    
    payload = {
        "video_id": video_id,
        "video_url": yt_url,
        "transcript": transcript
    }
    
    rabbit_channel = await rabbitMq.get_channel()

    queue = await rabbit_channel.declare_queue(
        QUEUE_NAME,
        durable=True
    )

    # Avoid blocking here. Iterating the queue waits indefinitely when it is empty.
    # The request can be published directly, and duplicate handling can be added later
    # with a persistent store or a separate non-blocking check.
    await rabbit_channel.default_exchange.publish(
        Message(
            body=json.dumps(payload).encode(),
            delivery_mode=2,      # persistent
        ),
        routing_key=queue.name
    )

    print("Quiz generation request pushed to RabbitMQ queue for processing.")
    
    return {"message": "Quiz generation request has been queued for processing. Please check after some time for the generated quiz."}