import json
import os
from db.connection import client
collection = client["quizDB"]["quizCollection"]
embedding_collection = client["quizDB"]["pineconeCollection"]
from llm import llm
from rabbitMQ import rabbitMq
from utility.logger import log

from dotenv import load_dotenv
load_dotenv()
MAX_LLM_TOKENS = int(os.getenv("MAX_LLM_TOKENS"))

QUEUE_NAME = "quiz_generation_queue"
PINECODE_EMBEDDING_QUEUE_NAME = "pinecode-embeddingqueue"
from services.pinecodeServices import generateAndStoreEmbeddings, generate_and_store_embeddings_from_transcript


async def process_message(message):
    async with message.process():

        body = json.loads(message.body.decode())
        video_id = body["video_id"]
        log(f"process_message: Received quiz generation message for video_id={video_id}")

        # a quick loop to check if the quiz already exists in the database
        existing_quiz = collection.find_one({"video_id": video_id})
        if existing_quiz:
            log(f"process_message: Quiz already exists for video_id={video_id}, skipping")
            return {"message": "Quiz already exists for the given video ID"}

        batchsum=0
        chunk = []
        response = []
        log(f"process_message: Starting transcript processing for video_id={video_id} ({len(body['transcript'])} segments)")
        for snippet in body["transcript"]:
            if snippet['text'] is not None:
                if(batchsum + len(snippet['text']) > MAX_LLM_TOKENS and len(chunk) > 0):
                    if len(response) == 0:
                        log(f"process_message: Sending first batch to LLM for video_id={video_id} (batch size: {len(chunk)} snippets)")
                        response = llm.generate_quiz(chunk)
                        if response["is_educational"] is False:
                            response["video_id"] = video_id
                            response["video_url"] = body["video_url"]
                            result = collection.insert_one(response)
                            log(f"process_message: Video {video_id} is NOT educational, quiz aborted")
                            return {"message": "The video content is not educational. Quiz generation aborted."}
                        log(f"process_message: First batch processed, video {video_id} is educational")
                    else:
                        log(f"process_message: Sending additional batch to LLM for video_id={video_id} (batch size: {len(chunk)} snippets)")
                        response["quiz"].extend(llm.generate_quiz(chunk)["quiz"])
                    chunk = [snippet]
                    batchsum = len(snippet['text'])
                elif batchsum + len(snippet['text']) <= MAX_LLM_TOKENS:
                        batchsum += len(snippet['text'])     
                        chunk.append(snippet)
        # Generate quiz for any remaining snippets
        if chunk and len(chunk) > 0:
            if len(response) == 0:
                log(f"process_message: Sending final batch to LLM for video_id={video_id} (batch size: {len(chunk)} snippets)")
                response = llm.generate_quiz(chunk)
                if response["is_educational"] is False:
                    response["video_id"] = video_id
                    response["video_url"] = body["video_url"]
                    result = collection.insert_one(response)
                    log(f"process_message: Video {video_id} is NOT educational, quiz aborted")
                    return {"message": "The video content is not educational. Quiz generation aborted."}
            else:
                log(f"process_message: Sending final batch to LLM for video_id={video_id} (batch size: {len(chunk)} snippets)")
                response["quiz"].extend(llm.generate_quiz(chunk)["quiz"])
        # append the video id to the response
        response["video_id"] = video_id
        response["video_url"] = body["video_url"]

        # save the response to mongo DB database
        result = collection.insert_one(response)
        response["id"] = str(result.inserted_id)
        log(f"process_message: Quiz generated and saved to database for video_id={video_id} (total questions: {len(response.get('quiz', []))})")
        return {"message": "Quiz generated successfully"}

async def process_embedding_generation_message(message):
    async with message.process():
        body = json.loads(message.body.decode())
        video_id = body["video_id"]
        log(f"process_embedding_generation_message: Received embedding generation message for video_id={video_id}")

        # check if embedding already generated
        result = embedding_collection.find_one({"video_id": video_id})
        if result and result["transcript_found"]:
            log(f"process_embedding_generation_message: Embeddings already exist for video_id={video_id}, skipping")
            return {"message" : "embedding already generated for video"} 
        
        # If manual_transcript was provided (from manual transcript fallback), use it directly
        # Otherwise, call the pinecode service (which will try to auto-fetch)
        if "manual_transcript" in body and body["manual_transcript"]:
            log(f"process_embedding_generation_message: Using pre-parsed manual transcript for video_id={video_id}")
            generate_and_store_embeddings_from_transcript(video_id, body["manual_transcript"])
        else:
            log(f"process_embedding_generation_message: Auto-fetching transcript for embedding generation for video_id={video_id}")
            generateAndStoreEmbeddings(video_id)
        log(f"process_embedding_generation_message: Embedding generation completed for video_id={video_id}")
        print(f"Embedding generation updated in database for video ID {video_id}")
        return {"message" : f"Embedding generation completed for video id {video_id}"}

async def start_consumer():
    rabbit_channel = await rabbitMq.get_channel()

    quiz_queue = await rabbit_channel.declare_queue(
        QUEUE_NAME,
        durable=True
    )
    embedding_queue = await rabbit_channel.declare_queue(
        PINECODE_EMBEDDING_QUEUE_NAME,
        durable=True
    )

    print("RabbitMQ consumer started")
    await quiz_queue.consume(process_message)
    await embedding_queue.consume(process_embedding_generation_message)