import instructor
from pydantic import BaseModel
from openai import OpenAI

# Define your desired output structure
class UserInfo(BaseModel):
    name: str
    age: int

def foo(x):
    # Patch the OpenAI client
    client = instructor.from_openai(OpenAI())

    # Extract structured data from natural language
    user_info = client.chat.completions.create(
        model="gpt-3.5-turbo",
        response_model=UserInfo,
        messages=[{"role": "user", "content": "John Doe is 30 years old."}],
    )

    return(user_info.name)