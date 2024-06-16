from pydantic import BaseModel, Field
from multiprocessing.pool import ThreadPool
from ai.util import openai_client

class ImprovementStrategies(BaseModel):
    strategies: list[str] = Field(description="A list of suggestions for ways to improving the message (for example, 'Use simpler language', 'Add a call to action', etc.)")

class MessageVariants(BaseModel):
    variants: list[str] = Field(description="A list of different proposed re-writes of the given message, based on the reason given.")    

def generate_variants(message: str):
    N_strategies = 5
    N_variants = 3

    strategies = openai_client().chat.completions.create(
        model="gpt-3.5-turbo",
        response_model=ImprovementStrategies,
        messages=[
            {
                "role": "system",
                "content": "You are an assistant who helps campaigns (for marketing, advocacy, public health, etc) write more effective public-facing messages. " + \
                           f"When the user provides a message, you should provide {N_strategies} suggestions for ways to improve the message."

            },
            {   "role": "user",
                "content": message},
        ],
    )

    def generate_variants_for_strategy(strategy):
        return openai_client().chat.completions.create(
            model="gpt-3.5-turbo",
            response_model=MessageVariants,
            messages=[
                {
                    "role": "system",
                    "content":  "You are an assistant who helps campaigns (for marketing, advocacy, public health, etc) write more effective public-facing messages. " + \
                               f"When the user provides a message, provide {N_variants} different proposed re-writes of the given message based on the following strategy: '{strategy}'."
                },
                {   "role": "user",
                    "content": message},
            ],
        )
    
    strategy_variants = ThreadPool(N_strategies).map(generate_variants_for_strategy, strategies.strategies)

    output = [
        {"strategy": strategy, "variants": variants.variants}
        for strategy, variants in zip(strategies.strategies, strategy_variants)
    ]

    return output

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    print(generate_variants("Buy cheese, it's healthy!"))