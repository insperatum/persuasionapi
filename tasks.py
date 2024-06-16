import os
from celery import Celery
from celery.utils.log import get_task_logger

from models import Task, Message, Prediction
from ai.generate import generate_variants
from ai.predict import predict_impact
from multiprocessing.pool import ThreadPool
import json

app = Celery('tasks', broker=os.getenv("CELERY_BROKER_URL"))
logger = get_task_logger(__name__)


@app.task
def analyze(task_id):
    task = Task.get(id=task_id)
    message = Message.create(
        source = "USER",
        value = task.input
    )

    suggestions = []
    all_variants = []

    for o in generate_variants(message.value):
        strategy = o["strategy"]; variants = o["variants"]
        variants = [
            Message.create(
                source = "BOT",
                value = variant
            )
            for variant in variants
        ]
        all_variants.extend(variants)
        suggestions.append({
            "strategy": strategy,
            "variants": variants
        })

    def create_prediction(message):
        prediction = Prediction.create(
            model = "gpt3.5-turbo",
            message = message,
            value = predict_impact(message.value)
        )
        return prediction.value

    variant_predictions = {k:v for k,v in ThreadPool(5).map(lambda v: (v.value, create_prediction(v)), all_variants)}
    for suggestion in suggestions:
        suggestion["score"] = sum([variant_predictions[variant.value] for variant in suggestion["variants"]]) / len(suggestion["variants"])

    # Filter to top 2 suggestions
    suggestions = sorted(suggestions, key=lambda s: s["score"], reverse=True)[:3]
    # Filter to top 2 variants per suggestion
    for suggestion in suggestions:
        suggestion["variants"] = sorted(suggestion["variants"], key=lambda v: variant_predictions[v.value], reverse=True)[:2]

    output = [
        {
            "strategy": suggestion["strategy"],
            # "score": suggestion["score"],
            "suggestions": [
                {
                    "message": variant.value,
                    "prediction": variant_predictions[variant.value]
                }
                for variant in suggestion["variants"]
            ]
        }
        for suggestion in suggestions
    ]
    

    task.output = json.dumps(output)
    task.save()