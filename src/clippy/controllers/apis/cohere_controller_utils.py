from typing import Callable

import cohere

from clippy.controllers.utils import truncate_left


def make_fn(generate_func, tokenize_func, model):
    """helper to make func for threadpool"""

    def _fn(x):
        """func that is actually called by threadpool

        this takes a prompt and returns the likelihood of that prompt (hence max_tokens=0)
        """
        if len(x) == 2:
            option, prompt = x
            return_likelihoods = "ALL"
        elif len(x) == 3:
            option, prompt, return_likelihoods = x

        while True:
            try:
                if len(tokenize_func(prompt)) > 2048:
                    prompt = truncate_left(tokenize_func, prompt)
                response = generate_func(prompt=prompt, max_tokens=0, model=model, return_likelihoods=return_likelihoods)
                return (response.generations[0].likelihood, option)
            except cohere.error.CohereError as e:
                print(f"Cohere fucked up: {e}")
                continue
            except ConnectionError as e:
                print(f"Connection error: {e}")
                continue

    return _fn


def _generate_func(co_client: cohere.Client) -> Callable:
    return co_client.generate


def _tokenize_func(co_client: cohere.Client) -> Callable:
    return co_client.tokenize
