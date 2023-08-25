import asyncio
from typing import Any, Dict, List, Optional, Tuple

from concurrent.futures import ThreadPoolExecutor

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from clippy.states import Task
from clippy.stubs.stubs import StubHelper, StubTemplates, Template


def _full_response(data: Any, obj: Any):
    class Raw(type(data)):
        pass

    raw = Raw(data)
    raw._response = obj
    return raw


# i thought this might be useful for debugging/iteration but it seems like i could rather just call the full method


def allow_full_response(func):
    async def wrapper(*args, **kwargs):
        resp = await func(*args, **kwargs)
        if args[0]._return_full:
            return _full_response(resp, resp)
        return resp

    return wrapper


class Controller:
    _is_async: bool = False
    _n_workers: int = 16
    _return_full: bool = False

    # ---
    client_exception: Exception = None
    client_exception_message: str = None
    model: str = None

    def __init__(self, *args, **kwargs):
        self._check()

    def __getattr__(self, name: str):
        return getattr(self.client, name)

    def _check(self):
        if self.model is None:
            print("WARNING: Model not set, probably needed for api")

    async def generate(self, prompt: str, *args, **kwargs):
        raise NotImplementedError

    async def embed(self, texts: List[str], *args, **kwargs):
        raise NotImplementedError

    def pick_action(self, template: Template, options: List[Dict[str, str]]):
        raise NotImplementedError

    async def score_actions(self, str_template: Template, options: List[Dict[str, str]], **kwargs):
        opt_strs = str_template.map(options, **kwargs)

        scores = await asyncio.gather(
            *[await self.generate(prompt=opt, max_tokens=0, return_likelihoods="ALL") for opt in opt_strs]
        )

        return [{**options[i], "score": s[0].likelihood} for i, s in enumerate(scores)]

    def next_action(self, elements: List[str]):
        state = StubTemplates.state

    # @allow_full_response
    async def score_text(self, text: str) -> float:
        resp = await self.generate(prompt=text, max_tokens=0, return_likelihoods="ALL")
        return resp[0].likelihood

    async def find_most_similar_str(
        self, objective: str, objectives: List[str] | List[Task], return_all: bool = False
    ) -> Tuple[float, str, Optional[np.ndarray]]:
        # get all the objectives
        if isinstance(objectives[0], Task):
            objectives = [t.objective for t in objectives if t.objective != objective]

        objectives = [objective] + objectives

        # embed them but stack so one call
        embedding_resp = await self.embed(objectives)
        embeddings = embedding_resp.embeddings

        # get the most similar
        scores = cosine_similarity([embeddings[0]], embeddings[1:]).flatten()
        argmax = np.argmax(scores)

        out = scores[argmax], objectives[argmax + 1]

        if return_all:
            out += (scores,)

        return out


# SYNC STUFF I DO NOT WANT ANYMORE
# example of how youd do this with async
def score_actions_sync(self, str_template: Template, options: List[Dict[str, str]], **kwargs):
    """score a list of strings"""
    opt_strs = str_template.map(options, **kwargs)
    opt_strs = [{"text": opt, "return_full": True} for opt in opt_strs]

    # to do this without threadpool use: [self.score_text(opt) for i, opt in enumerate(opt_strs)]
    with ThreadPoolExecutor(max_workers=self._n_workers) as executor:
        scores = executor.map(self.score_text, opt_strs)

    # transform to scores as its a generator and if i need to check if text matches with options input
    _scores = [(s[0].likelihood, s[0].text) for s in scores]
    return [{**options[i], "score": score[0]} for i, score in enumerate(_scores)]


def score_text(self, text: str, return_full: bool = False) -> float:
    """
    the most simple way to score a text is to generate it and return the likelihood
    """
    if isinstance(text, dict):
        text, return_full = text["text"], text["return_full"]

    score = self.generate(prompt=text, max_tokens=0, return_likelihoods="ALL")

    if return_full:
        return score

    return score[0].likelihood


def generate(self, prompt: str, *args, **kwargs):
    raise NotImplementedError
