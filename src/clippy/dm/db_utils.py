from dataclasses import asdict, is_dataclass
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Protocol

import tinydb
from tinydb.table import Document

from clippy.states.states import Task


class DC(Protocol):
    doc_id: Optional[int] = None


class Database(tinydb.TinyDB):
    _instance = None
    MemoryStorage = tinydb.storages.MemoryStorage

    # database config for when to save data
    _save_api_calls: bool = True

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance.__init__(*args, **kwargs)
        return cls._instance

    def __init__(self, path: Path | str = "db.json", save_api_calls: bool = True, *arg, **kwargs):
        super().__init__(path, *arg, **kwargs)
        self._save_api_calls = save_api_calls

    def save_dataclass(self, instance: DC) -> int:
        if not is_dataclass(instance):
            raise ValueError("Error, instance not a dataclass")

        table = self.table(instance.__class__.__name__.lower())

        if doc_id := getattr(instance, "doc_id", None) is not None:
            return table.upsert(Document(asdict(instance), doc_id=doc_id))[0]

        instance.doc_id = table.insert(asdict(instance))
        return instance.doc_id

    @classmethod
    def database_api_calls(cls, func: Callable):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            response = await func(self, *args, **kwargs)
            if (db := cls._instance) is not None and db._save_api_calls:
                db.save_dataclass(response)
            return response

        return wrapper
