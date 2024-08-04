from .util import * 
import pandas as pd
import concurrent.futures
import tqdm
import random
import pickle

writing_strategies = [
    "Appealing to people's common sense is important",
    "Challenging people's assumptions can provoke deeper thinking",
    "Authenticity is key to gaining trust",
    "Strategic exaggeration can capture attention",
    "Effective messaging uses clear, simple language",
    "Complex, sophisticated language can convey expertise and credibility",
    "Messages are more credible when they use facts and statistics",
    "Personal anecdotes are more relatable than facts and statistics",
    "Emotional stories can be more persuasive than logical arguments",
    "Logical arguments are more convincing than emotional stories",
    "Humor can be a powerful tool in messaging",
    "Serious tones convey importance and urgency",
    "Positive messages are more effective than negative ones",
    "Negative messages can be more motivating and compelling",
    "Appealing to shared values strengthens the message",
    "Highlighting differences in values can make the message stand out",
]

def compare_messages(
    original_message: str,
    modified_message: str,
    yes_no_question: str,
    logodds_threshold: float = 0,
    verbose: bool = False,
) -> bool:
    messages = [
        {
            "role": "user",
            "content": (
                "Consider the following two messages\n"
                f"<original_message>{original_message}</original_message>\n"
                f"<modified_message>{modified_message}</modified_message>\n"
                f"{yes_no_question}\n"
                "Answer only with 'YES' or 'NO'\n"
            )
        }
    ]
    res = llama(messages, temperature=0, return_full_response_object=True)
    logprobs = res["choices"][0]["logprobs"]["content"][0]["top_logprobs"]
    logprobs_map = {lp["token"]: lp["logprob"] for lp in logprobs}
    logodds_yes = logprobs_map.get("YES", -100)
    logodds_no = logprobs_map.get("NO", -100)
    if verbose:
        print(f"{logodds_yes=}, {logodds_no=}")
    logodds = logodds_yes - logodds_no
    return logodds > logodds_threshold

def sanitize(s):
    s = s.replace("{DEMOCRATIC_CANDIDATE}", "CANDIDATE_A")
    s = s.replace("{REPUBLICAN_CANDIDATE}", "CANDIDATE_B")
    s = s.replace("Democrats", "LEFT_GROUP")
    s = s.replace("Republicans", "RIGHT_GROUP")
    return s

def unsanitize(s):
    s = s.replace("CANDIDATE_A", "{DEMOCRATIC_CANDIDATE}")
    s = s.replace("CANDIDATE_B", "{REPUBLICAN_CANDIDATE}")
    s = s.replace("LEFT_GROUP", "Democrats")
    s = s.replace("RIGHT_GROUP", "Republicans")
    return s

def modify_message(
    original_message: str,
    question: str,
    desired_answer: str,
    undesired_answer: str,
    max_allowed_length_diff: float = 0.15,
    writing_advice: str = "",
    max_attempts: int = 10,
    verbose_logging: bool = False,
) -> str:
    n_chars_orig = len(sanitize(original_message))
    min_n_chars, max_n_chars = int(n_chars_orig * (1 - max_allowed_length_diff)), int(n_chars_orig * (1 + max_allowed_length_diff))
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert in political messaging. "
                "You know how to craft messages to make them maximally persuasive.\n"
                # "You are a political science researcher who studies the effectiveness of political messaging.\n"
                f"You are trying to convince the experiment subject to answer with\n"
                f"<desired_answer>{sanitize(desired_answer)}</desired_answer>\nto the question:\n"
                f"<question>{sanitize(question)}</question>\n"
                f"You want to NOT have the user answer with <undesired_answer>{sanitize(undesired_answer)}</undesired_answer>."
                f"Rewrite the message provided in the <original_message></original_message> XML tags\n"
                "to make it maximally likely to persuade the user to answer with the desired answer.\n"
                "Enclose the modified message in <modified_message></modified_message> XML tags."
            ),
        },
        {
            "role": "user",
            "content": (
                f"<original_message>{sanitize(original_message)}</original_message>\n"
                "Modify this message to make it more persuasive. The modified message should stay on the same general topic as the original\n"
                + (f"Use the following writing advice to guide your modifications:{writing_advice}\n" if writing_advice else "")
                + "Do not introduce any new factual claims that are not supported by the original message.\n"
                f"The modified message should be between {min_n_chars} and {max_n_chars} characters long - similar in length to the original message."
            )
        },
    ]
    for i in range(max_attempts):
        if verbose_logging:
            print(f"Generation attempt {i + 1}")
        res = llama(messages, temperature=1)
        if not res.startswith("<modified_message>") or not res.endswith("</modified_message>"):
            if verbose_logging:
                print(f"Invalid response format. {res=}")
            continue
        modified_message = res[len("<modified_message>"):-len("</modified_message>")].strip()
        if not (min_n_chars <= len(modified_message) <= max_n_chars):
            if verbose_logging:
                print(f"Message length outside desired range. {len(modified_message)=}, {min_n_chars=}, {max_n_chars=}")
            continue
        return unsanitize(modified_message)
    if verbose_logging:
        print("Failed to generate a valid response.")
    return None



def generate_n_alternatives(
    original_message: str,
    question: str,
    desired_answer: str,
    undesired_answer: str,
    writing_strategies: list[str] = writing_strategies,
    probability_of_using_writing_strategy: float = 0.5,
    max_attempts: int = 10,
    n: int = 10,
    callback = lambda pct: None
):
    modified_messages = []
    if not writing_strategies:
        writing_advice = [""] * n
    else:
        writing_advice = [
            (
                random.choice(writing_strategies)
                if random.random() < probability_of_using_writing_strategy
                else ""
            ) for _ in range(n)
        ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as executor:
        futures = [
            executor.submit(
                modify_message,
                original_message=original_message,
                question=question,
                desired_answer=desired_answer,
                undesired_answer=undesired_answer,
                writing_advice=writing_advice[i],
                max_attempts=max_attempts,
            ) for i in range(n)
        ]
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            callback(i / n)
        for future in futures:
            modified_messages.append(future.result())

    messages = [original_message] + [m for m in modified_messages if m is not None]
    # writing_advice = [""] + [writing_advice[i] for i, m in enumerate(modified_messages) if m is not None]
    # n_alternatives = list(zip(messages, preds, writing_advice))
    # n_alternatives = sorted(n_alternatives, key=lambda x: x[1], reverse=True)
    return messages