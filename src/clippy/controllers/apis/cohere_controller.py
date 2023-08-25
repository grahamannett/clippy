import asyncio
from os import environ
from typing import Coroutine, List

import cohere
from cohere.responses import Embeddings, Generation, Generations

from dataclasses import dataclass

from clippy.controllers.controller import Controller
from clippy.controllers.utils import truncate_left

AVAILABLE_MODELS = ["command-xlarge", "xlarge"]
DEFAULT_SPECIAL_TOKENS_INTS = {13782: ["click"], 5317: ["type"]}


@dataclass
class CohereConfig:
    model: str = "command-nightly"

    class embed:
        model: str = "embed-english-v2.0"
        truncate: str = "RIGHT"


class CohereController(Controller):
    model: str = "command-nightly"
    conf: CohereConfig = CohereConfig()
    cohere_client = None  # make it possible to get client without instantiating controller
    client: cohere.AsyncClient

    client_exception = cohere.error.CohereError
    client_exception_message = "Cohere fucked up: {0}"

    _is_async: bool = True

    def __init__(self, client: cohere.AsyncClient = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = client or CohereController.get_client()

    @staticmethod
    def get_client(api_key: str = None, check_api_key: bool = True) -> cohere.AsyncClient:
        api_key = api_key or environ.get("COHERE_KEY")
        return cohere.AsyncClient(api_key=api_key, check_api_key=check_api_key)

    async def embed(self, texts: List[str], truncate: str = None, model=None, **kwargs) -> Embeddings:
        truncate = truncate or self.conf.embed.truncate
        model = model or self.conf.embed.model
        return await self.client.embed(texts=texts, truncate=truncate, model=model)

    # @Database.capture(Generation)
    async def generate(
        self,
        prompt: str = None,
        model: str = None,
        temperature: float = 0.5,
        num_generations: int = 5,
        max_tokens: int = 20,
        stop_sequences: List[str] = None,
        return_likelihoods: str = "GENERATION",
        truncate: str = "START",  # must be one of NONE/START/END
        extra_print=False,
        **kwargs,
    ) -> cohere.client.Generations:
        # https://docs.cohere.com/reference/generate
        return await self.client.generate(
            prompt=prompt,
            model=model or self.conf.model,
            temperature=temperature,
            num_generations=num_generations,
            max_tokens=max_tokens,
            stop_sequences=stop_sequences,
            return_likelihoods=return_likelihoods,
            truncate=truncate,
            **kwargs,
        )

    def get_special_tokens(self, tokens: List[str] = ["click", "type"]):
        # not sure if i want to make Click/CLICK/etc as tokens as well
        special_tokens_dict = {}
        tokenized: cohere.client.Tokens = None

        for token in tokens:
            tokenized = self.tokenize(token)
            special_tokens_dict[tokenized.tokens[0]] = tokenized.token_strings

        return special_tokens_dict

    def close(self) -> Coroutine | None:
        return self.client.close()
