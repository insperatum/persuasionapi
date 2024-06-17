import os
import numpy as np
import pandas as pd
import tiktoken

from ai.util import openai_client, Content, Target

gpt_model = "gpt-4o"
n_prompts = 30

path = os.path.dirname(os.path.abspath(__file__))
df_prompt_templates = pd.read_csv(os.path.join(path, "prompt_templates.csv"))

if gpt_model == "gpt-4-1106-preview":
    enc = tiktoken.get_encoding("cl100k_base")
    assert(all(len(enc.encode(str(x)))==1 for x in range(501)))
    openai_tokens_cl100k_base = {str(x):enc.encode(str(x))[0] for x in [*range(501), "A", "B", "neither", "Neither"]}
    openai_tokens = openai_tokens_cl100k_base
if gpt_model == "gpt-4o":
    enc = tiktoken.get_encoding("o200k_base")
    assert(all(len(enc.encode(str(x)))==1 for x in range(501)))
    openai_tokens_o200k_base = {str(x):enc.encode(str(x))[0] for x in [*range(501), "A", "B", "neither", "Neither"]}
    openai_tokens = openai_tokens_o200k_base

def get_prompt_templates(population):
    if population in ["all", "us-adults"]:
        prompt_templates = df_prompt_templates
    elif population in ["democrat", "democrats"]:
        prompt_templates = df_prompt_templates[df_prompt_templates.profile_party=="Democrat"]
    elif population in ["republican", "republicans"]:
        prompt_templates = df_prompt_templates[df_prompt_templates.profile_party=="Republican"]
    elif population in ["independent", "independents"]:
        prompt_templates = df_prompt_templates[df_prompt_templates.profile_party=="Independent"]
    else:
        raise NotImplementedError() 
    
    assert len(prompt_templates) >= n_prompts
    return prompt_templates.prompt.to_list()[:n_prompts]

def run_model_with_seed(message, target, seed):
    
    valid_tokens = ["1", "2", "3", "4", "5"]

    logit_bias = {openai_tokens[str(k)]:100 for k in valid_tokens}

    prompt_templates = get_prompt_templates(target.audience)
    prompt = prompt_templates[seed].format(CONDITION_TEXT=message, OUTCOME_TEXT=target.question, LOWER_LABEL=target.lower, UPPER_LABEL=target.upper)

    completion = openai_client().chat.completions.create(
        model=gpt_model,
        messages=[
                {"role": "user", "content": prompt},
            ],
        max_tokens=1,
        logit_bias=logit_bias,
        n=20,
    )

    samples = [int(x.message.content) for x in completion.choices]
    expectation = np.mean(samples)

    return expectation

def predict(content: Content, target: Target):
    preds = [run_model_with_seed(content.message, target, seed) for seed in range(n_prompts)]
    prediction = np.mean(preds)
    return prediction
