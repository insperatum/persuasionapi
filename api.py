from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from models import Task
from tasks import analyze
import json

app = FastAPI()
# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

@app.get("/")
async def root():
    return {"message": "Hello World"}

class GenerateRequest(BaseModel):
    message: str
@app.post("/generate")
def generate(generate_request: GenerateRequest):
    message = generate_request.message
    task = Task.create(input=message)
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