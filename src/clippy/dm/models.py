import uuid
from typing import Any, Dict, List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column
from sqlmodel import JSON, Field, SQLModel


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
