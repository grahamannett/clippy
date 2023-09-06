import uuid
from typing import Any, Dict, List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column
from sqlmodel import JSON, Field, SQLModel

from sqlalchemy import text
from sqlalchemy_utils import create_database, database_exists
from sqlmodel import JSON, Field, MetaData, Session, SQLModel, create_engine, text
import sqlalchemy


# class BaseModel(SQLModel):
#     @classmethod
#     def capture(cls, **kwargs) -> "Base":
#         raise NotImplementedError


class Generation(SQLModel, table=True):
    # id: str = Field(default=None, primary_key=True)
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    prompt: str = Field(default=None)

    meta: Dict = Field(default={}, sa_column=Column(JSON))

    def __init__(self, *args, **kwargs) -> None:
        if "meta" in kwargs:
            id = kwargs["meta"]["id"]
            prompt = kwargs["meta"]["prompt"]
        super().__init__(*args, id=id, prompt=prompt, **kwargs)


class Embedding(SQLModel, table=True):
    key: Optional[int] = Field(default=None, primary_key=True)
    # id: str = Field(default=None, primary_key=True)
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        # primary_key=True,
        index=True,
        nullable=False,
    )
    text: str = Field(default=None)
    embedding: List[float] = Field(sa_column=Column(Vector()))
    meta: Dict = Field(default={}, sa_column=Column(JSON))

    @classmethod
    def from_response(cls, response: Dict[str, Any]) -> List["Embedding"]:
        embeddings = []
        texts, embs = response.pop("texts"), response.pop("embeddings")
        for text, emb in zip(texts, embs):
            embeddings.append(cls(text=text, embedding=emb, meta=response))
        return embeddings

    def __init__(self, text: str, embedding: List[float], _id: uuid.UUID = None, **kwargs) -> None:
        super().__init__(id=kwargs["meta"]["id"] or _id, text=text, embedding=embedding, **kwargs)


class Item(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    embedding: List[float] = Field(sa_column=Column(Vector(3)))


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
        with sqlalchemy.create_engine(
            "postgresql://postgres@localhost:5432", isolation_level="AUTOCOMMIT"
        ).connect() as connection:
            connection.execute(f"CREATE DATABASE {table_name}")


class DatabaseHooks:
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
