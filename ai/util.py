import instructor
from openai import OpenAI

_openai_client = []
def openai_client():
    if not _openai_client:
        _openai_client.append(instructor.from_openai(OpenAI()))
    return _openai_client[0]