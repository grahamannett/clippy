import asyncio
from typing import Any, Dict, List, Optional, Tuple, Protocol

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


class ClientProtocol(Protocol):
    async def embed(self, texts: List[str], *args, **kwargs):
        ...

    async def generate(self, prompt: str, *args, **kwargs):
        ...


class Controller:
    class Clients:
        pass

    class config:
        model: str = None

    _is_async: bool = False
    _n_workers: int = 16
    _return_full: bool = False

    # ---
    client: ClientProtocol
    client_exception: Exception = None
    client_exception_message: str = None

    def __init__(self, *args, **kwargs):
        self._check()

    def __getattr__(self, name: str):
        return getattr(self.client, name)

    async def end(self):
        return await self.client.close()

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
        tasks = [self.generate(prompt=opt, max_tokens=0, return_likelihoods="ALL") for opt in options]
        scores = await asyncio.gather(*tasks)
        return scores

    async def score_text(self, text: str) -> float:
        response = await self.generate(prompt=text, max_tokens=0, return_likelihoods="ALL")
        return response[0].likelihood

    async def find_most_similar_str(
        self, objective: str, objectives: List[str] | List[Task]
    ) -> Tuple[float, str, np.ndarray]:
        # Check if objectives are instances of Task and filter out the current objective
        objectives = [t.objective for t in objectives if isinstance(t, Task) and t.objective != objective]

        # Add the current objective to the start of the list
        objectives.insert(0, objective)

        # Embed all objectives in a single call
        embedding_resp = await self.embed(objectives)
        embeddings = embedding_resp.embeddings

        # Calculate cosine similarity scores
        scores = cosine_similarity([embeddings[0]], embeddings[1:]).flatten()

        # Find the most similar objective
        most_similar_index = np.argmax(scores)
        most_similar_score, most_similar_objective = scores[most_similar_index], objectives[most_similar_index + 1]

        # Return the most similar objective and its score, along with all scores if requested
        return (most_similar_score, most_similar_objective, scores)
