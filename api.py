from typing import Union, List
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Request, Depends
from fastapi import Security, HTTPException
import fastapi
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware

from flask import Flask, render_template, request, render_template_string
import os
from pydantic import BaseModel, Field
from fastapi.responses import RedirectResponse

import httpx
from models import Task, Job, User
from tasks import analyze, run_job
import json
import secrets

flask_app = Flask(__name__)
flask_app.secret_key = os.getenv('FLASK_SECRET_KEY', "super-secret")

@flask_app.route('/')
def main():
    return render_template('landing.html')

@flask_app.route('/demo')
def demo():
    return render_template('demo.html')

@flask_app.route('/login')
def login():
    return render_template('login.html')

@flask_app.route('/llamathon')
def llamathon():
    return render_template('llamathon.html')

CLERK_API_KEY = os.getenv('CLERK_API_KEY')
CLERK_BASE_URL = 'https://api.clerk.dev/v1'
def get_user(token: str):
    headers = {
        'Authorization': f'Bearer {CLERK_API_KEY}'
    }
    response = httpx.get(f'{CLERK_BASE_URL}/sessions/{token}', headers=headers)
    if response.status_code != 200:
        return None
    session = response.json()
    user_id = session["user_id"]
    user_response = httpx.get(f'{CLERK_BASE_URL}/users/{user_id}', headers=headers)
    if user_response.status_code != 200:
        return None
    return user_response.json()

@flask_app.route("/user")
def user():
    regenerate_api_key = request.args.get("regenerate_api_key")
    token = request.cookies.get("clerk-session")
    clerk_user = get_user(token)
    if not clerk_user:
        return "Invalid token", 401
    user_id = clerk_user['id']
    # Get or create the user
    user, created = User.get_or_create(id=user_id)

    if regenerate_api_key:
        user.api_key = secrets.token_hex(32)
        user.save()

    return render_template_string("""
        {% if api_key %}
            <p>Your API Key: {{ api_key }}</p>
        {% endif %}
        <a href="{{ url_for('user', regenerate_api_key=1) }}">Regenerate API Key</a>
    """, api_key=user.api_key)





# description = """
# An API for simulated RCTs
# """ # This can be many lines, markdown

tags_metadata = [
    {
        "name": "compare",
        "description": "Run an RCT simulation",
    },
    {
        "name": "revise",
        "description": "Revise a message",
    },
    {
        "name": "job",
        "description": "Get the result of a job",
    },
]

app = FastAPI(
    title="Attitude API",
    summary="An API for simulated RCTs",
    openapi_tags=tags_metadata,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

app.mount("/web", WSGIMiddleware(flask_app))

api_key_header = APIKeyHeader(name="X-API-Key")
def get_user_from_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == "pilot":
        user = User.get_or_create(id="pilot")
    user = User.get_or_none(api_key=api_key_header)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    return user

@app.get("/", include_in_schema=False)
async def redirect_example():
    return RedirectResponse(url="/web")

@app.get("/demo", include_in_schema=False)
async def redirect_example():
    return RedirectResponse(url="/web/demo")

@app.get("/login", include_in_schema=False)
async def redirect_example():
    return RedirectResponse(url="/web/login")

@app.get("/llamathon", include_in_schema=False)
async def redirect_example():
    return RedirectResponse(url="/web/llamathon")

@app.post("/predict", include_in_schema=False)
async def predict(message:str = Form(""), file: Union[UploadFile, None] = None, model:str = Form(""), question:str = Form(""), lower:str = Form(""), upper:str = Form(""), audience:str = Form("us-adults")):
    # TODO add validation
    if not file and not message: return {"message": "No data sent"}
    if file: file = await file.read()

    task = Task.create(command="predict", input=message, file=file, model=model, question=question, lower=lower, upper=upper, audience=audience)
    analyze.delay(task.id)
    return {"task_id": task.id}

@app.post("/generate", include_in_schema=False)
async def generate(message:str = Form(""), file: Union[UploadFile, None] = None, model:str = Form(""), question:str = Form(""), lower:str = Form(""), upper:str = Form(""), audience:str = Form("us-adults")):
    # TODO add validation
    if not file and not message: return {"message": "No data sent"}
    if file: file = await file.read()

    task = Task.create(command="generate", input=message, file=file, model=model, question=question, lower=lower, upper=upper, audience=audience)
    analyze.delay(task.id)
    return {"task_id": task.id}

class TaskRequest(BaseModel):
    task_id: str
    
@app.post("/status", include_in_schema=False)
def status(task_request: TaskRequest):
    task = Task.get(id=task_request.task_id)
    if task.output is None:
        return {
            "task_id": task.id,
            "input": task.input,
            "progress": task.progress,
            "status": "running",
        }
    else:
        return {
            "task_id": task.id,
            "input": task.input,
            "status": "completed",
            "output": json.loads(task.output),
        }
    




#### New API ####

class Content(BaseModel):
    name: str = Field(..., description="Content identifier", example="animal_intelligence")
    text: str = Field(..., description="The text of the content", example="Animals are highly intelligent. For example, crows can solve complex puzzles.")

class Outcome(BaseModel):
    question: str = Field(..., description="A target attitude", example="Should the government strengthen or weaken animal protection laws?")
    label_good: str = Field(..., description="The scale label for the most desired outcome", example="strengthened")
    label_bad: str = Field(..., description="The scale label for the least desired outcome", example="weakened")

class CompareInput(BaseModel):
    contents: List[Content] = Field(..., description="A list of all contents to be compared")
    outcomes: List[Outcome] = Field(..., description="A list of all outcomes to be compared")

class OutputItem(BaseModel):
    job_id: str


@app.post("/compare", response_model=OutputItem, tags=["compare"])
async def compare(data: CompareInput, user: User = Depends(get_user_from_api_key)):
    if user.credit == 0:
        raise HTTPException(
            status_code=fastapi.status.HTTP_403_FORBIDDEN,
            detail="Unauthorized"
        )
    job = Job.create(command="compare", input=data.model_dump())
    run_job.delay(job.id)
    return {"job_id": job.id}


class ReviseInput(BaseModel):
    content: Content = Field(..., description="A piece of content to revised")
    outcome: Outcome = Field(..., description="The target outcome")

@app.post("/revise", response_model=OutputItem, tags=["revise"])
async def revise(data: ReviseInput, user: User = Depends(get_user_from_api_key)):
    if user.credit == 0:
        raise HTTPException(
            status_code=fastapi.status.HTTP_403_FORBIDDEN,
            detail="Unauthorized"
        )
    job = Job.create(command="revise", input=data.model_dump())
    run_job.delay(job.id)
    return {"job_id": job.id}

@app.post("/job", tags=["job"])
def job(job_id: str):
    job = Job.get(id=job_id)
    if job.output is None:
        return {
            "job_id": job.id,
            "input": job.input,
            "status": "running",
            "progress": job.progress,
        }
    else:
        return {
            "job_id": job.id,
            "input": job.input,
            "status": "completed",
            "output": job.output,
        }