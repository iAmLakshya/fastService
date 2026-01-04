from datetime import UTC, datetime
from typing import Any, ClassVar, Self
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def generate_id() -> str:
    return str(uuid4())


class BaseDocument(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        arbitrary_types_allowed=True,
    )

    id: str = Field(default_factory=generate_id, alias="_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    __collection_name__: ClassVar[str]

    def to_document(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_none=True)

    @classmethod
    def from_document(cls, doc: dict[str, Any]) -> Self:
        return cls.model_validate(doc)

    def update_timestamp(self) -> None:
        object.__setattr__(self, "updated_at", datetime.now(UTC))


class SoftDeletableDocument(BaseDocument):
    is_deleted: bool = False
    deleted_at: datetime | None = None

    def soft_delete(self) -> None:
        object.__setattr__(self, "is_deleted", True)
        object.__setattr__(self, "deleted_at", datetime.now(UTC))

    def restore(self) -> None:
        object.__setattr__(self, "is_deleted", False)
        object.__setattr__(self, "deleted_at", None)
