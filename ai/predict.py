from pydantic import BaseModel, Field
from multiprocessing.pool import ThreadPool
from ai.util import openai_client

class Prediction(BaseModel):
    prediction: int = Field(description="A prediction for how impactful the message will be, from 1 (not at all impactful) to 100 (extremely impactful)") 

def predict_impact(message: str):
    prediction = openai_client().chat.completions.create(
        model="gpt-3.5-turbo",
        response_model=Prediction,
        messages=[
            {
                "role": "system",
                "content": "You are an assistant who helps campaigns (for marketing, advocacy, public health, etc) write more effective public-facing messages. " + \
                           "When the user provides a message, you should provide a prediction for how impactful the message will be, from 1 (not at all impactful) to 100 (extremely impactful)."
            },
            {   "role": "user",
                "content": message},
        ],
    )
    return prediction.prediction

