from typing import Union
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware

from flask import Flask, render_template, request
import os
from pydantic import BaseModel
from fastapi.responses import RedirectResponse


from models import Task
from tasks import analyze
import json

flask_app = Flask(__name__)
flask_app.secret_key = os.getenv('FLASK_SECRET_KEY', "super-secret")

@flask_app.route('/')
def main():
    return render_template('landing.html')

@flask_app.route('/demo')
def demo():
    return render_template('demo.html')

app = FastAPI()
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


@app.post("/generate")
async def generate(message:str = Form(""), file: Union[UploadFile, None] = None):
    if not file and not message:
        return {"message": "No data sent"}

    if file:
        file = await file.read()
    task = Task.create(input=message, file=file)
    analyze.delay(task.id)
    return {"task_id": task.id}


class TaskRequest(BaseModel):
    task_id: str
@app.post("/task")
def task(task_request: TaskRequest):
    task = Task.get(id=task_request.task_id)
    if task.output is None:
        return {
            "task_id": task.id,
            "input": task.input,
            "status": "pending",
        }
    else:
        return {
            "task_id": task.id,
            "input": task.input,
            "status": "completed",
            "output": json.loads(task.output),
        }