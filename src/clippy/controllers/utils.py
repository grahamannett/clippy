from typing import Callable

def truncate_left(tokenize: Callable, prompt: str, *rest_of_prompt, limit: int = 2048):
    i = 0
    chop_size = 5
    print(f"WARNING: truncating sequence of length {len(tokenize(prompt + ''.join(rest_of_prompt)))} to length {limit}")
    while len(tokenize(prompt + "".join(rest_of_prompt))) > limit:
        prompt = prompt[i * chop_size :]
        i += 1
    return prompt

