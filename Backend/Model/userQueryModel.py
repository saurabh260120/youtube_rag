from fastapi import FastAPI
from pydantic import BaseModel
class userQueryItem(BaseModel):
    youtubeUrl: str
    user_question: str