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


class Controller:
    class Clients:
        pass

    class config:
        model: str = None

    _is_async: bool = False
    _n_workers: int = 16
    _return_full: bool = False

    # ---
    client_exception: Exception = None
    client_exception_message: str = None

    def __init__(self, *args, **kwargs):
        self._check()

    def __getattr__(self, name: str):
        return getattr(self.client, name)

    def _check(self):
        if self.config.model is None:
            print("WARNING: Model not set, probably needed for api")

    async def generate(self, prompt: str, *args, **kwargs):
        raise NotImplementedError

    async def embed(self, texts: List[str], *args, **kwargs):
        raise NotImplementedError

    def pick_action(self, template: Template, options: List[Dict[str, str]]):
        raise NotImplementedError

    async def score_options(self, options: List[str], **kwargs):
        scores = await asyncio.gather(
            *[self.generate(prompt=opt, max_tokens=0, return_likelihoods="ALL") for opt in options]
        )
        return scores

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
