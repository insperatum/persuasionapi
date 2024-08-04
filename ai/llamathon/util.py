import requests
import json
import os
import time

FIREWORKS_API_KEY = "Af1aRv9n8ykxM3YDG6kJuE7rse8ZMxhFGmYQLBRMZmrrK2aZ"
ATTITUDE_API_KEY = "pilot"

def llama(messages, temperature=0.6, return_full_response_object: bool = False):    
    url = "https://api.fireworks.ai/inference/v1/chat/completions"
    payload = {
        "model": "accounts/fireworks/models/llama-v3p1-405b-instruct",
        "max_tokens": 16384,
        "top_p": 1,
        "top_k": 40,
        "presence_penalty": 0,
        "frequency_penalty": 0,
        "temperature": temperature,
        "messages": messages,
        "logprobs": return_full_response_object,
        "top_logprobs": 5 if return_full_response_object else None,
    }
    headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {FIREWORKS_API_KEY}"
    }
    response = requests.request("POST", url, headers=headers, data=json.dumps(payload)).json()
    if return_full_response_object:
        return response
    return response['choices'][0]['message']['content']