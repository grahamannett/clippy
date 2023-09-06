import json
import unittest

import numpy as np
from sqlmodel import Session, select

from clippy.dm.db_utils import Database
from clippy.dm.sql_models import DatabaseConfig, DatabaseSetup, Embedding, Generation
from clippy.states.actions import Actions
from clippy.states.states import Task


class TestDatabase(unittest.IsolatedAsyncioTestCase):
    def test_tasks(self):
        db = Database(storage=Database.MemoryStorage)
        task = Task.from_page(objective="test", url="https://google.com")

        action = Actions(action="click", selector="input")

        breakpoint()

    # def test_data(self):


class TestSQLDatabase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        with open("tests/db_fixtures/responses/generate.json") as f:
            self.generation_meta = json.load(f)
        with open("tests/db_fixtures/responses/embed.json") as f:
            self.embedding_meta = json.load(f)
        return super().setUp()

    @unittest.skip("no longer using SQL")
    def test_models(self):
        db_config = DatabaseConfig(database_name="testdb")
        db = DatabaseSetup(config=db_config, echo=False)
        engine = db.setup()

        db.add(Generation(meta=self.generation_meta))

        embeddings = Embedding.from_response(self.embedding_meta)
        db.add(*embeddings)

        with Session(engine) as session:
            statement = select(Embedding)
            result = session.exec(statement).first()

            self.assertIsInstance(result.embedding, np.ndarray)
