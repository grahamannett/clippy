import os

from typing import List
import openai

from clippy.controllers.controller import Controller

MODELS_AVAILABLE

class OpenAIController(Controller):
    model = "gpt-3.5-turbo"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if (openai_key := os.environ.get("OPENAI_API_KEY", None)) is None:
            raise KeyError("No OpenAI Key, This must be set if you want to use")

        self.openai.api_key = openai_key

        # set as propoerty for accessible way to use openai without import
        self.client = openai

    async def generate_async(self, prompt: str, *args, **kwargs):
        return await openai.Completion.acreate(prompt=prompt)

    def embed(self, texts: List[str], **kwargs):
        return openai.Embedding.create(texts, **kwargs)

    async def embed_async(self, texts: List[str]):
        resp = await openai.Embedding.acreate()
