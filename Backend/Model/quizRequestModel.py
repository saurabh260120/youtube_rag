from fastapi import FastAPI
from pydantic import BaseModel
class QuizRequestItem(BaseModel):
    youtubeUrl: str
    startTime: str
    endTime: str