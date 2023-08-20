import asyncio
from typing import Coroutine, List

import cohere
from cohere.responses import Generations, Generation, Embeddings

from clippy.controllers.apis.cohere_controller_utils import make_fn
from clippy.controllers.controller import Controller
from clippy.dm.db_utils import Database


AVAILABLE_MODELS = ["command-xlarge-20221108", "xlarge"]
DEFAULT_SPECIAL_TOKENS_INTS = {13782: ["click"], 5317: ["type"]}


class cohere_config:
    class embed:
        model: str = "embed-english-v2.0"
        truncate: str = "RIGHT"


class Generation:
    def __init__(self, response: Generation | Generations):
        if isinstance(response, Generations):
            response = response[0]

        self.data = {
            "id": response.id,
            "prompt": response.prompt,
            "text": response.text,
            "likelihood": response.likelihood,
            "token_likelihoods": [{"token": t, "likelihood": l} for t, l in response.token_likelihoods],
        }


class Embedding:
    def __init__(self, response: Embeddings):
        breakpoint()
        self.data = {
            "id": response.id,
            "embedding": response.embedding,
        }


class CohereController(Controller):
    model: str = "command-xlarge-20221108"
    cohere_client = None  # make it possible to get client without instantiating controller
    client: cohere.AsyncClient | cohere.Client = None

    client_exception = cohere.error.CohereError
    client_exception_message = "Cohere fucked up: {0}"

    def __init__(self, client: cohere.Client | cohere.AsyncClient, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = client

        self._is_async = True if isinstance(client, cohere.AsyncClient) else False

        if CohereController.cohere_client is None:
            CohereController.cohere_client = client  # should make a singleton?

        self._fn = make_fn(generate_func=self.generate, tokenize_func=self.tokenize, model=self.model)

    @staticmethod
    def get_client(api_key: str, check_api_key: bool = True) -> cohere.Client:
        return cohere.Client(api_key=api_key, check_api_key=check_api_key)

    @staticmethod
    def get_client_async(api_key: str, check_api_key: bool = True) -> cohere.Client:
        return cohere.AsyncClient(api_key=api_key, check_api_key=check_api_key)

    @Database.capture(Embedding)
    def embed(
        self, texts: List[str], truncate: str = cohere_config.embed.truncate, model=cohere_config.embed.model, **kwargs
    ) -> Embeddings:
        return self.client.embed(texts=texts, truncate=truncate, model=model)

    @Database.capture(Embedding)
    async def embed_async(
        self, texts: List[str], truncate: str = cohere_config.embed.truncate, model=cohere_config.embed.model, **kwargs
    ) -> Embeddings:
        return await self.client.embed(texts=texts, truncate=truncate, model=model)

    @Database.capture(Generation)
    async def generate_async(
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
            model=model if model else self.model,
            temperature=temperature,
            num_generations=num_generations,
            max_tokens=max_tokens,
            stop_sequences=stop_sequences,
            return_likelihoods=return_likelihoods,
            truncate=truncate,
            **kwargs,
        )

    @Database.capture(Generation)
    def generate(
        self,
        prompt: str,
        model: str = None,
        temperature: float = 0.5,
        num_generations: int = 5,
        max_tokens: int = 20,
        stop_sequences: List[str] = None,
        return_likelihoods: str = "GENERATION",
        truncate: str = "START",  # must be one of NONE/START/END
        **kwargs,
    ) -> cohere.client.Generations:
        # https://docs.cohere.com/reference/generate

        return self.client.generate(
            prompt=prompt,
            model=model if model else self.model,
            temperature=temperature,
            num_generations=num_generations,
            max_tokens=max_tokens,
            stop_sequences=stop_sequences,
            return_likelihoods=return_likelihoods,
            truncate=truncate,
            **kwargs,
        )

    def tokenize(self, text: str) -> cohere.client.Tokens:
        return self.client.tokenize(text=text)

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


if __name__ == "__main__":
    from os import environ

    from scipy.spatial.distance import cosine

    async def main():
        client = CohereController.get_client_async(api_key=environ["COHERE_KEY"])
        controller = CohereController(client=client)
        resp = await controller.generate_async(prompt="hello world", num_generations=1)

        email = "fake email example"
        embeddings = await controller.embed_async(texts=[f"Write me a polite email responding to the one below: {email}. Response:"])
        await controller.client.close()

    asyncio.run(main())
