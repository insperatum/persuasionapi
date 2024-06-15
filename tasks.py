import os
from celery import Celery
from celery.utils.log import get_task_logger

from models import AddResult

app = Celery('tasks', broker=os.getenv("CELERY_BROKER_URL"))
logger = get_task_logger(__name__)



@app.task
def add(x, y):
    logger.info(f'Adding {x} + {y}')
    result = x + y
    AddResult.create(x=x, y=y, result=result)
    return result
