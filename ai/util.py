from openai import OpenAI
import os

_openai_client = []
def openai_client():
    if not os.getenv('OPENAI_API_KEY'):
        from dotenv import load_dotenv
        load_dotenv()
                
    if not _openai_client:
        _openai_client.append(OpenAI())
    return _openai_client[0]