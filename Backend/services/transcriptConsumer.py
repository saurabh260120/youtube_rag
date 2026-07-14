import json
import os
from db.connection import client
collection = client["quizDB"]["quizCollection"]
embedding_collection = client["quizDB"]["pineconeCollection"]
from llm import llm
from rabbitMQ import rabbitMq

from dotenv import load_dotenv
load_dotenv()
MAX_LLM_TOKENS = int(os.getenv("MAX_LLM_TOKENS"))

QUEUE_NAME = "quiz_generation_queue"
PINECODE_EMBEDDING_QUEUE_NAME = "pinecode-embeddingqueue"
from services.pinecodeServices import generateAndStoreEmbeddings


async def process_message(message):
    async with message.process():

        body = json.loads(message.body.decode())

        #started reprocessing for video id: {body["video_id"]} and url: {body["video_url"]}
        print(f"Started processing for video id: {body['video_id']}")

        # a quick loop to check if the quiz already exists in the database
        existing_quiz = collection.find_one({"video_id": body["video_id"]})
        if existing_quiz:
            print(f"Quiz already exists for video id: {body['video_id']}")
            return {"message": "Quiz already exists for the given video ID"}

        batchsum=0
        chunk = []
        response = []
        for snippet in body["transcript"]:
            if snippet['text'] is not None:
                if(batchsum + len(snippet['text']) > MAX_LLM_TOKENS and len(chunk) > 0):
                    if len(response) == 0:
                        response = llm.generate_quiz(chunk)
                        if response["is_educational"] is False:
                            response["video_id"] = body["video_id"]
                            response["video_url"] = body["video_url"]
                            result = collection.insert_one(response)
                            # move to the next item in queue
                            print(f"Video content is not educational for video id: {body['video_id']}. Quiz generation aborted.")
                            return {"message": "The video content is not educational. Quiz generation aborted."}
                    else:
                        response["quiz"].extend(llm.generate_quiz(chunk)["quiz"])
                    chunk = [snippet]
                    batchsum = len(snippet['text'])
                elif batchsum + len(snippet['text']) <= MAX_LLM_TOKENS:
                        batchsum += len(snippet['text'])     
                        chunk.append(snippet)
        # Generate quiz for any remaining snippets
        if chunk and len(chunk) > 0:
            if len(response) == 0:
                response = llm.generate_quiz(chunk)
                if response["is_educational"] is False:
                    response["video_id"] = body["video_id"]
                    response["video_url"] = body["video_url"]
                    result = collection.insert_one(response)
                    print(f"Video content is not educational for video id: {body['video_id']}. Quiz generation aborted.")
                    return {"message": "The video content is not educational. Quiz generation aborted."}
            else:
                response["quiz"].extend(llm.generate_quiz(chunk)["quiz"])
        # print(f"LLM response: {response}")
        # append the video id to the response
        response["video_id"] = body["video_id"]
        response["video_url"] = body["video_url"]

        # save the response to mongo DB database
        result = collection.insert_one(response)
        response["id"] = str(result.inserted_id)
        print(f"Quiz generated and saved to database for video id: {body['video_id']}")
        return {"message": "Quiz generated successfully"}

async def process_embedding_generation_message(message):
    async with message.process():
        body = json.loads(message.body.decode())
        video_id = body["video_id"]
        print(f"Started processing for embedding generation for video id: {body['video_id']}")

        # check if embedding already generated
        result = embedding_collection.find_one({"video_id": video_id})
        if result and result["transcript_found"]:
            print(f"embedding already exist for video_id {video_id}")
            return {"message" : "embedding already generated for video"} 
        
        # call the pinecode service to generate and store embeddings
        generateAndStoreEmbeddings(body['video_id'])
        print(f"Embedding generation completed for video id: {video_id}")
        embedding_collection.update_one(
            {"video_id": video_id},
            {"$set": {"transcript_found": True}},
            upsert=True,
        )
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