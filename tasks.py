import os
from celery import Celery
from celery.utils.log import get_task_logger

from models import Task
from ai.generate import generate_variants

app = Celery('tasks', broker=os.getenv("CELERY_BROKER_URL"))
logger = get_task_logger(__name__)

@app.task
def analyze(task_id):

    task = Task.get(id=task_id)
    message = task.input
    
    output = generate_variants(message)

    task.output = output
    task.save()