from dataclasses import dataclass
from typing import Callable, List
import tinydb
import asyncio

from clippy.states.states import Task


class Generation:
    # def __init__(self, response: "Generation" | "Generations"):
    def __init__(self, response):
        # if isinstance(response, "Generations"):
        #     response = response[0]

        self.data = {
            "id": response.id,
            "prompt": response.prompt,
            "text": response.text,
            "likelihood": response.likelihood,
            "token_likelihoods": [{"token": t, "likelihood": l} for t, l in response.token_likelihoods],
        }


class Embedding(tinydb.Table):
    def __init__(self, response):
        self.data = {
            "id": response.id,
            "embedding": response.embedding,
        }


class Tasks(tinydb.Table):
    tasks: List[Task] = []


class Database:
    db: tinydb.TinyDB
    MemoryStorage = tinydb.storages.MemoryStorage

    Generation = Generation
    Embedding = Embedding

    def __init__(self, database_path: str = "data/db/db.json"):
        self.db = tinydb.TinyDB(database_path)

    def __call__(self, *args, **kwargs):
        return self.db
