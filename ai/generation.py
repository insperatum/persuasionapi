from typing import Optional
from pydantic import BaseModel, Field
from multiprocessing.pool import ThreadPool
from ai.util import openai_client, Target
import instructor

def generate_variants(message: str):
    N_strategies = 5
    N_variants = 3

    class ImprovementStrategies(BaseModel):
        strategies: list[str] = Field(description="A list of suggestions for ways to improving the message (for example, 'Use simpler language', 'Add a call to action', etc.)")

    strategies = instructor.from_openai(openai_client()).chat.completions.create(
        model="gpt-4o",
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
        class MessageVariants(BaseModel):
            variants: list[str] = Field(description="A list of different proposed re-writes of the given message, based on the reason given.")    

        return  instructor.from_openai(openai_client()).chat.completions.create(
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



class Generation(BaseModel):
    message: str
    reason: str
    original_section: Optional[str]
    highlight_section: Optional[str]
    highlight_start: Optional[int]
    highlight_end: Optional[int]

def generate_mutations(message: str, n: int=8): #target:Target, n: int=3):
    N_variants = n

    class MessageVariant(BaseModel):
        highlight_section_initial: str = Field(description="A section of the original message that could be improved.")
        reason: str = Field(description="A suggestion about how the highlighted section could be improved.")
        highlight_section_new: str = Field(description="A proposed new version of the initial highlighted section.")
        message: str = Field(description="A proposed new version of the full message, with the highlighted section replaced by the new section.")

    class MessageVariants(BaseModel):
        variants: list[MessageVariant] = Field(description="A list of different proposed re-writes of the given message")


    message_variants = instructor.from_openai(openai_client()).chat.completions.create(
        model="gpt-4o",
        response_model=MessageVariants,
        messages=[
            {
                "role": "system",
                "content": "You are an assistant who helps campaigns design more effective public-facing messages. " + \
                        #    "The goal of the campaign is to "
                           f"When the user provides a message, provide {N_variants} different proposed edits to the given message. " + \
                            "Each edit should be small and focused on improving a specific part of the message."

            },
            {   "role": "user",
                "content": message},
        ],
    )

    def parse(variants):
        for message_variant in variants:
            # start_idx = message_variant.message.find(message_variant.highlight_section_new)
            # end_idx = start_idx + len(message_variant.highlight_section_new)
            if message_variant.highlight_section_initial not in message:
                continue
            
            new_message = message.replace(message_variant.highlight_section_initial, message_variant.highlight_section_new)
            start_idx = new_message.find(message_variant.highlight_section_new)
            end_idx = start_idx + len(message_variant.highlight_section_new)

            yield Generation(
                # message = message_variant.message,
                message = new_message,
                reason = message_variant.reason,
                original_section = message_variant.highlight_section_initial,
                highlight_section = message_variant.highlight_section_new,
                highlight_start = start_idx,
                highlight_end = end_idx,
            )
    
    return [x for x in parse(message_variants.variants)]

    # output = {
    #     "variants": [
    #         {
    #             "highlight_section_initial": variant.highlight_section_initial,
    #             "highlight_section_new": variant.highlight_section_new,
    #             "reason": variant.reason,
    #             "message": variant.message
    #         }
    #         for variant in message_variants.variants

    #     ]
    # }

    # return output

