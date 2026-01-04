from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator


def _validate_uuid(value: str) -> str:
    UUID(value)
    return value


TodoId = Annotated[str, AfterValidator(_validate_uuid)]
UserId = Annotated[str, AfterValidator(_validate_uuid)]
