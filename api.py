from typing import Union, List
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware

from flask import Flask, render_template, request
import os
from pydantic import BaseModel
from fastapi.responses import RedirectResponse


from models import Task, Job
from tasks import analyze, run_job
import json

flask_app = Flask(__name__)
flask_app.secret_key = os.getenv('FLASK_SECRET_KEY', "super-secret")

@flask_app.route('/')
def main():
    return render_template('landing.html')

@flask_app.route('/demo')
def demo():
    return render_template('demo.html')



# description = """
# An API for simulated RCTs
# """ # This can be many lines, markdown

tags_metadata = [
    {
        "name": "compare",
        "description": "Run an RCT simulation",
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

@app.get("/", include_in_schema=False)
async def redirect_example():
    return RedirectResponse(url="/web")

@app.get("/demo", include_in_schema=False)
async def redirect_example():
    return RedirectResponse(url="/web/demo")

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
    name: str
    text: str

class Outcome(BaseModel):
    question: str
    label_good: str
    label_bad: str

class CompareInput(BaseModel):
    contents: List[Content]
    outcomes: List[Outcome]

class OutputItem(BaseModel):
    job_id: str


@app.post("/compare", response_model=OutputItem, tags=["compare"])
async def compare(data: CompareInput):
    job = Job.create(command="compare", input=data.model_dump())
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