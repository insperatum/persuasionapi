from pydantic import BaseModel, Field
from multiprocessing.pool import ThreadPool
from ai.util import openai_client
import instructor

class Prediction(BaseModel):
    prediction: int = Field(description="A prediction for how impactful the message will be, from 1 (not at all impactful) to 100 (extremely impactful)") 

def predict_impact(model:str, message: str, question:str, lower:str, upper:str, audience:str):
    # TODO: Implement model
    prediction = instructor.from_openai(openai_client()).chat.completions.create(
        model="gpt-3.5-turbo",
        response_model=Prediction,
        messages=[
            {
                "role": "system",
                "content": "You are an assistant who helps campaigns write more effective public-facing messages.\n" + \
                          f"The target audience is:\n> {audience}.\n\nThe outcome question is:\n> {question}\n('{lower}' to '{upper}')\n(Where the intended answer is {upper})\n" + \
                           "When the user provides a message, you should provide a prediction for how impactful the message will be, from 1 (not at all impactful) to 100 (extremely impactful)."
            },
            {   "role": "user",
                "content": message},
        ],
    )
    return prediction.prediction

