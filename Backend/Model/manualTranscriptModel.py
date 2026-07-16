from pydantic import BaseModel


class ManualTranscriptRequest(BaseModel):
    youtubeUrl: str
    transcript: str