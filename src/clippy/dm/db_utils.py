from dataclasses import dataclass
from typing import Callable, List
import tinydb
import asyncio

from sqlalchemy import text
from sqlalchemy_utils import create_database, database_exists
from sqlmodel import JSON, Field, MetaData, Session, SQLModel, create_engine, text
import sqlalchemy



@dataclass
class DatabaseConfig:
    url: str = "postgresql+psycopg2://localhost"
    database_name: str = "clippy"

    capture_responses: bool = False


class DatabaseSetup:
    """
    this class is a bit unnecessary but i need a stub for testing
    """

    def __init__(
        self,
        config: DatabaseConfig = DatabaseConfig(),
        echo: bool = True,
    ):
        url = f"{config.url}/{config.database_name}"

        if not database_exists(url):
            create_database(url)

        self.engine = create_engine(url=url, echo=echo)
        self.metadata_obj = MetaData()

    def setup(self):
        # install the extension for vectors
        with self.engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()

        # drop and recreate the tables
        SQLModel.metadata.drop_all(self.engine)
        SQLModel.metadata.create_all(self.engine)
        return self.engine

    def add(self, *items: SQLModel):
        with Session(self.engine) as session:
            for item in items:
                session.add(item)
            session.commit()

    def make_table(self, table_name: str = "testdb") -> None:
        with sqlalchemy.create_engine("postgresql://postgres@localhost:5432", isolation_level="AUTOCOMMIT").connect() as connection:
            connection.execute(f"CREATE DATABASE {table_name}")


class Database:
    db = tinydb.TinyDB("data/db/db.json")

    def __init__(self):
        pass



    # decorator to capture response and insert into database
    @classmethod
    def capture(cls, model):
        def decorator(func: Callable):
            if not DatabaseConfig.capture_responses:
                return func

            async def wrapper(*args, **kwargs):
                response = func(*args, **kwargs)

                if asyncio.iscoroutine(response):
                    response = await response

                if len(response) > 1:
                    raise ValueError("Error, response too long to capture")

                inst = model(response=response)
                cls.db.insert(inst.data)
                return response

            return wrapper

        return decorator
