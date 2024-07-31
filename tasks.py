import os
from celery import Celery
from celery.utils.log import get_task_logger

import ai
from models import Task, Job
# from multiprocessing.pool import ThreadPool
import threading
import concurrent.futures
import json

app = Celery('tasks', broker=os.getenv("CELERY_BROKER_URL"))
logger = get_task_logger(__name__)


@app.task
def run_job(job_id:str):
    job = Job.get(id=job_id)

    job.progress = 10; job.save()

    if job.command == "compare":
        import time
        time.sleep(5)
        job.progress = 20; job.save()
        time.sleep(5)
        job.progress = 30; job.save()
        time.sleep(5)
        
        content = job.input['content']
        question = job.input['question']
        lower = job.input['lower']
        upper = job.input['upper']

        output = [
            {"name": c['name'], "foo": 4}
            for c in content
        ]
        job.output = output
        job.progress = 100
        job.save()

        return job.output

@app.task
def analyze(task_id:str):
    task = Task.get(id=task_id)

    task.progress = 10
    task.save()

    model = task.model
    content = ai.Content(message = task.input, video = task.file)
    target = ai.Target(question=task.question, lower=task.lower, upper=task.upper, audience=task.audience)
    ai.preprocess(model, content, target)

    task.progress = 15
    task.save()

    output = {"message": content.message}
    
    if task.command == "predict":
        prediction = ai.predict(model, content, target)
        output["prediction"] = prediction
        task.output = json.dumps(output)
        task.progress = 100
        task.save()
        return output

    if task.command == "generate":
        prediction = ai.predict(model, content, target)
        output["prediction"] = prediction
        task.progress = 20

        variants = {x.message: x for x in ai.generate_mutations(content.message, 5)}

        task.progress = 30
        task.save()

        # with ThreadPool(5) as pool:
        #     predictions = pool.map(lambda x: ai.predict(model, ai.Content(message=x), target), variants.keys())
        #     predictions = {x: y for x, y in zip(variants.keys(), predictions)}

        def task_callback(n_complete, lock):
            with lock:
                n_complete[0] += 1
                print(f'Progress: {n_complete}/{len(variants)} tasks completed')
                task.progress = 30 + int(70 * n_complete[0] / len(variants))
                task.save()
        def get_pred(variant):
            return ai.predict(model, ai.Content(message=variant.message), target)
        
        n_complete = [0]
        lock = threading.Lock()

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for variant in variants.values():
                future = executor.submit(get_pred, variant)
                future.add_done_callback(lambda fut: task_callback(n_complete, lock))
                futures.append(future)

            concurrent.futures.wait(futures)

        predictions = {k: future.result() for k, future in zip(variants.keys(), futures)}
        message_variants = sorted(variants.values(), key=lambda v: predictions[v.message], reverse=True)[:3]

        output["variants"] = [
            {**message_variant.model_dump(), "prediction": predictions[message_variant.message]}
            for message_variant in message_variants
        ]
        task.output = json.dumps(output)
        task.save()
        return output