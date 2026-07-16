from llm import llm
from rabbitMQ import rabbitMq

from db.connection import client
from services.pinecodeServices import getresultfromPinecodeDB
from dotenv import load_dotenv
from aio_pika import Message
import json
import os
from utility.logger import log

load_dotenv()
PINECODE_EMBEDDING_QUEUE_NAME = "pinecode-embeddingqueue"

# collection to check if vector embeddings exist for a given video ID
collection = client["quizDB"]["pineconeCollection"]
async def answerQuery(video_id, user_question):
    log(f"answerQuery: Processing query for video_id={video_id}, question='{user_question[:50]}...'")
    # Implement the logic to answer the user's query based on the YouTube video ID
    result = collection.find_one({"video_id": video_id})
    if result and result["transcript_found"]:
        # video exist in pincode db, fetch embeddings fro pinecode db and pass to llm to get the answer
        log(f"answerQuery: Video {video_id} found in pinecone database, fetching embeddings...")
        docs = getresultfromPinecodeDB(video_id, user_question)
        log(f"answerQuery: Retrieved {len(docs)} relevant documents for video_id={video_id}")
        answer = llm.answer_query(docs, user_question)
        log(f"answerQuery: Answer generated successfully for video_id={video_id}")
        return answer
    elif result and not result["transcript_found"]:
        # video exist in pincode db but transcript not found, return error message
        log(f"answerQuery: Video {video_id} found in DB but transcript not found")
        return {"message": "Transcript not found for the given video ID. Cannot answer the query."}
    else:
        # video does not exist in pincode db
        #push to the queue for generation of embeddings and return a message to the user
        log(f"answerQuery: Video {video_id} not found in pinecone DB, pushing to embedding queue...")
        rabbit_channel = await rabbitMq.get_channel()
        queue =  await rabbit_channel.declare_queue(
            PINECODE_EMBEDDING_QUEUE_NAME,
            durable=True
        )

        payload = {
            "video_id": video_id,
        }

        await rabbit_channel.default_exchange.publish(
            Message(
                body=json.dumps(payload).encode(),
                delivery_mode=2,      # persistent
            ),
            routing_key=queue.name
        )
        log(f"answerQuery: Embedding generation message published to queue for video_id={video_id}")

        return {"message": "Embeddings generation in progress for the given video ID. Please try again after some time."}