import unittest
import json
import numpy as np

from sqlmodel import select, Session
from clippy.dm.models import Generation, Embedding
from clippy.dm.db_utils import DatabaseConfig, DatabaseSetup


class TestDatabase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        with open("tests/db_fixtures/responses/generate.json") as f:
            self.generation_meta = json.load(f)
        with open("tests/db_fixtures/responses/embed.json") as f:
            self.embedding_meta = json.load(f)
        return super().setUp()

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
