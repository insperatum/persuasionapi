import os
from typing import Optional
from openai import OpenAI
from pydantic import BaseModel

_openai_client = []
def openai_client() -> OpenAI:
    if not os.getenv('OPENAI_API_KEY'):
        from dotenv import load_dotenv
        load_dotenv()

    if not _openai_client:
        _openai_client.append(OpenAI())
    return _openai_client[0]

class Content(BaseModel):
    message: str
    video: Optional[object] = None

class Target(BaseModel):
    question: str
    lower: str
    upper: str
    audience: str