import os
from celery import Celery
from celery.utils.log import get_task_logger

from models import AddResult, Request
from api import generate

app = Celery('tasks', broker=os.getenv("CELERY_BROKER_URL"))
logger = get_task_logger(__name__)

@app.task
def add(x, y):
    logger.info(f'Adding {x} + {y}')
    result = x + y
    AddResult.create(x=x, y=y, result=result)

    bar = generate.foo()
    print("Bar:", bar)
    return bar


@app.task
def analyze(request_id):
    request = Request.get(id=request_id)
    message = request.input
    logger.info(f'Improving: {message}')
    import time
    time.sleep(10)

    output = message + "!!!"
    request.output = output
    request.save()