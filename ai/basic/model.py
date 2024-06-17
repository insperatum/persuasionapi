from ai.util import openai_client, Content, Target
import instructor
from pydantic import BaseModel, Field

class Prediction(BaseModel):
    prediction: int = Field(description="A prediction for how impactful the message will be on the target outcome, from -100 (extremely negatively impactful) to 100 (extremely positively impactful)") 

def predict(content: Content, target: Target) -> float:
    prediction = instructor.from_openai(openai_client()).chat.completions.create(
        model="gpt-3.5-turbo",
        response_model=Prediction,
        messages=[
            {
                "role": "system",
                "content": "You are an assistant who helps campaigns write more effective public-facing messages.\n" + \
                        f"The target audience is:\n> {target.audience}.\n\nThe outcome question is:\n> {target.question}\n('{target.lower}' to '{target.upper}')\n(Where the intended answer is {target.upper})\n" + \
                        "When the user provides a message, you should provide a prediction for how impactful the message will be on the target outcome, from -100 (extremely negatively impactful) to 100 (extremely positively impactful)"
            },
            {   "role": "user",
                "content": content.message},
        ],
    )

    return prediction.prediction