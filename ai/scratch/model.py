import pandas as pd
import concurrent.futures
import tqdm
import requests 
import numpy as np
import backoff
from scipy.special import logsumexp
import random
import tiktoken
import os 

N_PROMPTS = 20

if not os.getenv('OPENAI_API_KEY'):
    from dotenv import load_dotenv
    load_dotenv()
BASETEN_API_KEY = os.getenv('BASETEN_API_KEY')
FIREWORKS_API_KEY = os.getenv('FIREWORKS_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

enc = tiktoken.get_encoding("o200k_base")
assert(all(len(enc.encode(str(x)))==1 for x in range(501)))
openai_tokens_o200k_base = {str(x):enc.encode(str(x))[0] for x in range(501)}

enc = tiktoken.get_encoding("cl100k_base")
assert(all(len(enc.encode(str(x)))==1 for x in range(501)))
openai_tokens_cl100k_base = {str(x):enc.encode(str(x))[0] for x in [*range(501), "A", "B", "neither", "Neither"]}


path = os.path.dirname(os.path.abspath(__file__))
possible_profiles = list(pd.read_csv(os.path.join(path, "profiles.csv")).T.to_dict().values())
random.seed(0)
profiles = random.sample(possible_profiles, N_PROMPTS)

random.seed(1)
for profile in profiles:
    profile["flip_outcome"] = random.choice([True, False])

random.seed(2)
intros = [
        "(For the following, keep in mind that the public has diverse attitudes and behaviors; people often provide very different answers to the same question.)",
        "(For the following, keep in mind that people's beliefs and behaviors are malleable; their answers to questions often change based on the framing or information provided.)",
        "(As you complete the following task, keep in mind what is known about the public's beliefs and behaviors from research in the field of behavioral science)",
        "(Keep in mind what is known about the public's beliefs and behaviors from research in the field of social psychology)",
        "(We are interested in predicting how people respond to questions and interventions in social science research studies.)",
        "(We are interested in predicting the treatment effect of different messages on research participants' attitudes, beliefs, and behaviors.)",
        "You will be asked to predict how people respond to various messages",
        "Can reading a message affect people’s attitudes and actions?",
        "Try to be accurate when you make predictions about how different messages affect how people think and behave",
        "As you complete the following task, take the perspective of a leading expert in social science."
    ]
for profile in profiles:
    profile["intro"] = random.choice(intros)

class PredictiveModel:
    def __init__(self, model_id: str):
        self.model_id = model_id

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=8)
    def run(self, system_prompt:str, user_prompt:str):
        if self.model_id.startswith("accounts/fireworks/models/"):
            url = "https://api.fireworks.ai/inference/v1/completions"
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {FIREWORKS_API_KEY}"
            }
            data = {
                "model": self.model_id,
                "max_tokens": 1,
                "prompt": f"{system_prompt}\n-----\n{user_prompt}\n-----ANSWER: ",
                "logprobs": 5
            }
            valid_tokens = ["1", "2", "3", "4", "5"]
            resp = requests.post(url, headers=headers, json=data)
            logprobs = {int(k):v
                        for k,v in resp.json()['choices'][0]['logprobs']['top_logprobs'][0].items()
                        if k in valid_tokens}
            # print(logprobs)
        else:
            if self.model_id.startswith("gpt"):
                url = "https://api.openai.com/v1/chat/completions"
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_API_KEY}"}
                if self.model_id.startswith("gpt-4o"):
                    logit_bias = {openai_tokens_o200k_base[str(k)]:100 for k in ["1", "2", "3", "4", "5"]}
                else:
                    logit_bias = {openai_tokens_cl100k_base[str(k)]:100 for k in ["1", "2", "3", "4", "5"]}
                valid_tokens = ["1", "2", "3", "4", "5"]
            else:
                url = f"https://model-{self.model_id}.api.baseten.co/production/predict"
                headers={"Authorization": f"Api-Key {BASETEN_API_KEY}"}
                logit_bias = {"16":100, "17":100, "18":100, "19":100, "20":100} # These are llama tokens 1,2,3,4,5
                valid_tokens = ["1", "2", "3", "4", "5"]


            data = {
                "messages": [
                    {"role":"system", "content": system_prompt},
                    {"role":"user", "content": user_prompt},
                ],
                "max_tokens":1,
                "logprobs":True,
                "top_logprobs":5,
                "logit_bias":logit_bias
            }
            if self.model_id.startswith("gpt"):
                data["model"] = self.model_id

            resp = requests.post(url, headers=headers, json=data)
            try:
                logprobs = {int(x['token']):x['logprob']
                            for x in resp.json()['choices'][0]['logprobs']['content'][0]['top_logprobs']
                            if x['token'] in valid_tokens}
            except Exception as e:
                print("Error")
                print(resp.json())
                raise e
        z = logsumexp(list(logprobs.values()))
        probs = {k:np.exp(v-z) for k,v in logprobs.items()}
        expectation = sum(k*v for k,v in probs.items())
        # print(".", end="")
        return expectation

    def predict(self, message: str, target_attitude: str, min_label:str, max_label:str) -> float:
        def run_profile(profile):
            system_prompt = (
f"""{profile['intro']}

You are an adult in the United States. Your profile is as follows:
- Age: {profile['age_5']}
- Gender: {'female' if profile['female'] else 'male'}
- Education: {profile['educ_5']}
- Ethnicity: {profile['race_4']}
- Party: {profile['pid_7']}
- Ideology: {profile['ideo_3']}

You will be described a scenario and then asked a question.
Give your answer immediately, as a number."""
            )

            min_label_ = max_label if profile["flip_outcome"] else min_label
            max_label_ = min_label if profile["flip_outcome"] else max_label
            
            user_prompt = (
f"""You are taking an online survey.

On the first page it says:
{message}

On the second page it says:
> {target_attitude}
Please answer with your own opinion, on a scale from 1 ({min_label_}) to 5 ({max_label_})
"""
            )

            val = self.run(system_prompt, user_prompt)
            if profile["flip_outcome"]:
                val = 6-val
            return val

        # vals = [run_profile(profile) for profile in profiles]
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            vals = list(executor.map(run_profile, profiles))
        return {"profile_values":vals, "prediction": np.mean(vals)}
    

# model_name = "Llama 3 8B Instruct vllm"
# model_id = "nwxly8yw"
# model_name = "gpt-4o-mini"
# model_id = "gpt-4o-mini"
# model_name = "Llama 3.1 70B Instruct"
# model_id = "8w6xen0w"
# model_name = "Llama 3.1 405B Instruct"
# model_id = "accounts/fireworks/models/llama-v3p1-405b-instruct"



    

def predict(message: str, target_attitude: str, min_label:str, max_label:str, model_id="gpt-4o-mini"):
    predictive_model = PredictiveModel(model_id=model_id)
    result = predictive_model.predict(message, target_attitude, min_label, max_label)
    # return (result["prediction"]-1)/4
    return result["prediction"]

# if __name__ == "__main__":
#     instances = pd.read_csv("~/projects/persuasion-data/output/all_instances.csv")

#     def f(row):
#         result = predictive_model.predict(row['content'], row['question'], row['min_label'], row['max_label'])
#         return {"instance_id": row['instance_id'], **result}

#     filename = f"/Users/lbh/projects/persuasion-data/output/all_predictions_{model_name}.csv"
#     if os.path.exists(filename):
#         df = pd.read_csv(filename)
#         print("Skipping", len(df), "existing predictions")
#     else:
#         df = pd.DataFrame(columns=["instance_id"])

#     with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
#         print("Predicting...")
#         futures = [executor.submit(f, row)
#                    for _, row in instances.iterrows()
#                    if row['instance_id'] not in df.instance_id.values]
#         for i, future in enumerate(tqdm.tqdm(concurrent.futures.as_completed(futures), total=len(futures))):
#             result = future.result()
#             df = pd.concat([df, pd.DataFrame([result])], ignore_index=True)
#             if (i % 10 == 0) or (i == len(futures)-1):
#                 df.to_csv(filename, index=False)