import os
from celery import Celery
from celery.utils.log import get_task_logger

import ai
from models import Task, Job
# from multiprocessing.pool import ThreadPool
import threading
import concurrent.futures
import json
import pandas as pd

app = Celery('tasks', broker=os.getenv("CELERY_BROKER_URL"))
logger = get_task_logger(__name__)


def get_predictions(contents, outcomes, callback=lambda pct: None, model_id=None):
    from ai.scratch.model import predict

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {}
        for i, content in enumerate(contents):
            for j, outcome in enumerate(outcomes):
                future = executor.submit(predict, content["text"], outcome["question"], outcome["label_bad"], outcome["label_good"], **({"model_id": model_id} if model_id else {}))
                futures[future] = (i, j)

        df = pd.DataFrame()
        for k, future in enumerate(concurrent.futures.as_completed(futures)):
            i, j = futures[future]
            df = pd.concat([df, pd.DataFrame([{"i": i, "j": j, "prediction": future.result()}])])
            pct = k / len(futures)
            callback(pct)
        
    predictions = []
    for i, content in enumerate(contents):
        predictions.append(df[df.i == i].prediction.mean())

    import numpy as np
    predictions = np.array(predictions)
    predictions_demean = predictions - predictions.mean()
    # We want softmax(predictions_demean * 1.914452)
    probs = np.exp(predictions_demean * 1.914452) / np.exp(predictions_demean * 1.914452).sum()

    # if predictions.std() == 0:
    #     zs = (predictions - predictions.mean())
    # else:
    #     zs = (predictions - predictions.mean()) / predictions.std()

    output = [
        {"name": content["name"], "prob": prob, "mean": mean}
        for content, prob, mean in zip(contents, probs, (predictions-1)/4*100)
    ]
    return output

@app.task
def run_job(job_id:str):
    print(f"Running job {job_id}")
    job = Job.get(id=job_id)
    print(f"Command: {job.command}")
    print(f"Input: {job.input}")

    job.progress = 10; job.save()

    try:
        if job.command == "compare":
            # model_id = job.input.get("model_id")
            contents = job.input['contents']
            outcomes = job.input['outcomes']

            def callback(pct):
                job.progress = 10 + int(90 * pct); job.save()
            output = get_predictions(contents, outcomes, callback)

            job.output = output
            job.progress = 100
            job.save()

            return job.output
        
        elif job.command == "revise":
            from ai.llamathon.model import generate_n_alternatives
            print("Generating suggestions...")
            job.output = "Generating alternatives..."; job.save()
            def callback(pct):
                print("Progress:", pct, "%")
                job.progress = 10 + int(60 * pct); job.save()

            model_id = job.input.get("model_id")
            content = job.input["content"]
            outcome = job.input["outcome"]
            alternatives = generate_n_alternatives(
                original_message = content["text"],
                question = outcome["question"],
                desired_answer = outcome["label_good"],
                undesired_answer = outcome["label_bad"],
                callback = callback
            )
            print("Finished generating alternatives")


            job.output = "Simulating human responses..."; job.save()
            contents = [{"name": f"message{i}", "text": alternative} for i, alternative in enumerate(alternatives)]
            outcomes = [
                {"question": outcome["question"], "label_good": outcome["label_good"], "label_bad": outcome["label_bad"]}
            ]
            def callback(pct):
                job.progress = 70 + int(20 * pct); job.save()
            predictions = get_predictions(contents, outcomes, callback)

            best = max(predictions, key=lambda x: x["prob"])
            best_message = [x['text'] for x in contents if x['name'] == best['name']][0]

            preds = get_predictions(
                [
                    {"name": "original_message", "text": content["text"]},
                    {"name": "revised_message", "text": best_message}
                ],
                outcomes,
                **({"model_id": model_id} if model_id else {})
            )

            output = {
                "revised_message": best_message,
                "prob": preds[1]["prob"],
                "original_mean": preds[0]["mean"],
                "mean": preds[1]["mean"]
            }
            
            job.output = output
            job.progress = 100
            job.save()
            return job.output
        
        else:
            raise ValueError(f"Invalid command: {job.command}")


    except Exception as e:
        job.output = {
            "job_id": job.id,
            "input": job.input,
            "progress": job.progress,
            "status": "failed",
        }
        job.save()
        raise e

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