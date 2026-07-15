
import asyncio

from utility.youtubeUrlToId import urlToId
from utility.youtubeDuration import get_video_duration
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from Model.quizRequestModel import QuizRequestItem
from Model.userQueryModel import userQueryItem

from services.quizGenerationService import generateQuiz
from services.transcriptConsumer import start_consumer
from services.answerQueryService import answerQuery

# import db connection
from db.connection import client

app = FastAPI()

from dotenv import load_dotenv
import os

load_dotenv()

allow_origins = os.getenv("ALLOWED_CORS_ORIGINS", "").split(",")


app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = client["quizDB"]
collection = db["quizCollection"]


@app.get("/")
async def root():
    return {"message": "Hello World, I am Up and running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(start_consumer())

@app.post("/generateQuiz")
async def generate_quiz(quiz_request: QuizRequestItem):
    duration = get_video_duration(quiz_request.youtubeUrl)
    if duration > 1800:
        print("Only videos under half hour are supported.")
        return {"message": "This application currently supports videos up to half hour long. Longer videos require significantly more llm calls so they aren't supported on the current free tier."}
    return await generateQuiz(quiz_request.youtubeUrl)

#feature 2
# user query a youtube video after pasting a link
@app.post("/userQuery")
async def user_query(user_query: userQueryItem):
    duration = get_video_duration(user_query.youtubeUrl)
    if duration > 3600:
        print("Only videos under 1 hour are supported.")
        return {"message": "This application currently supports videos up to 1 hour long. Longer videos require significantly more embedding requests, so they aren't supported on the current free tier."}
    video_id = urlToId(user_query.youtubeUrl)
    return await answerQuery(video_id, user_query.user_question)