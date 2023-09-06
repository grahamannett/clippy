from dataclasses import dataclass
from os import environ
from typing import Coroutine, Dict, List, Type

import cohere
from cohere.client import Embeddings, Generations

from clippy.controllers.controller import Controller
from clippy.controllers.utils import allow_full_response

AVAILABLE_MODELS = ["command-xlarge", "xlarge"]
DEFAULT_SPECIAL_TOKENS = {13782: ["click"], 5317: ["type"]}

import torch


class Responses:
    """
    A class to hold the response types.
    """

    Generations: Type[Generations] = Generations
    Embeddings: Type[Embeddings] = Embeddings


@dataclass
class CohereConfig:
    """
    A dataclass to hold the configuration for the Cohere API.
    """

    class embed:
        """
        A nested class to hold the configuration for the embedding model.
        """

        model: str = "embed-english-v2.0"
        truncate: str = "END"  # one of NONE|START|END

    model: str = "command"
    truncate: str = "END"  # one of NONE|START|END


class CohereController(Controller):
    """
    A class to interact with the Cohere API.
    """

    conf: CohereConfig = CohereConfig()
    cohere_client = None  # make it possible to get client without instantiating controller
    client: cohere.AsyncClient

    client_exception: Type[cohere.error.CohereError] = cohere.error.CohereError
    client_exception_message: str = "Cohere fucked up: {0}"

    _is_async: bool = True
    _calls = 0

    def __init__(self, client: cohere.AsyncClient = None, *args, **kwargs):
        """
        Initialize the CohereController.
        """
        super().__init__(*args, **kwargs)
        self.client = client or CohereController.get_client()

    def _get_special_tokens(self, tokens: List[str] = ["click", "type"]) -> Dict[int, List[str]]:
        """
        Get the special tokens. not sure if i want to make Click/CLICK/etc as tokens as well
        """
        special_tokens_dict: Dict[int, List[str]] = {}

        for token in tokens:
            tokenized: cohere.client.Tokens = self.tokenize(token)
            special_tokens_dict[tokenized.tokens[0]] = tokenized.token_strings

        return special_tokens_dict

    @staticmethod
    def get_client(api_key: str = None, check_api_key: bool = True) -> cohere.AsyncClient:
        """
        Get the Cohere client.
        """
        api_key = api_key or environ.get("COHERE_KEY")
        return cohere.AsyncClient(api_key=api_key, check_api_key=check_api_key)

    @allow_full_response(lambda resp: resp.tokens)
    async def tokenize(self, text, model: str = None):
        return await self.client.tokenize(
            text,
            model=model or self.conf.model,
        )

    async def embed(self, texts: List[str] | str, truncate: str = None, model: str = None, **kwargs) -> Embeddings:
        """
        Embed the given texts.
        """
        if isinstance(texts, str):
            texts = [texts]

        response = await self.client.embed(
            texts=texts, truncate=truncate or self.conf.embed.truncate, model=model or self.conf.embed.model, **kwargs
        )
        return response

    async def generate(
        self,
        prompt: str = None,
        model: str = None,
        temperature: float = 0.5,
        num_generations: int = None,
        max_tokens: int = 20,
        stop_sequences: List[str] = None,
        return_likelihoods: str = "GENERATION",
        truncate: str = "NONE",  # must be one of NONE/START/END
        # **kwargs,
    ) -> Generations:
        """
        Generate text using the Cohere API.
        """
        # https://docs.cohere.com/reference/generate

        response = await self.client.generate(
            prompt=prompt,
            model=model or self.conf.model,
            temperature=temperature,
            num_generations=num_generations,
            max_tokens=max_tokens,
            stop_sequences=stop_sequences,
            return_likelihoods=return_likelihoods,
            truncate=truncate,
            # **kwargs,
        )
        torch.save(response, f"test_output/cohere_responses/{self._calls}.pt")
        self._calls += 1
        return response

    async def close(self) -> Coroutine:
        """
        Close the Cohere client.
        """
        return await self.client.close()
