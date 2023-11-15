from dataclasses import asdict, is_dataclass
from functools import wraps
from pathlib import Path
from typing import Callable, Optional, Protocol

import tinydb
from tinydb.table import Document

from clippy import logger


class DC(Protocol):
    doc_id: Optional[int] = None


class Database(tinydb.TinyDB):
    _instance = None
    MemoryStorage = tinydb.storages.MemoryStorage
    Query = tinydb.Query
    Table = tinydb.database.Table

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

    @classmethod
    def _get_table(cls, instance: DC) -> Table:
        table_name = instance.__class__.__name__.lower()
        return cls._instance.table(table_name)

    def save_dataclass(self, instance: DC, table: Table = None) -> int:
        if not is_dataclass(instance):
            raise ValueError("Error, instance not a dataclass")

        if table is None:
            table = Database._get_table(instance)

        doc_id = getattr(instance, "doc_id", None)

        if doc_id != None:
            upserted_doc = table.upsert(Document(asdict(instance), doc_id=doc_id))
            return upserted_doc[0]

        instance.doc_id = table.insert(asdict(instance))
        return instance.doc_id

    def load_all(self):
        pass

    @classmethod
    def database_api_calls(cls, func: Callable):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            response = await func(self, *args, **kwargs)
            if (db := cls._instance) is not None and db._save_api_calls:
                table = Database._get_table(response)
                doc_id = db.save_dataclass(response, table=table)
                logger.info(f"inserted {doc_id} into {table.name}")
            return response

        return wrapper
