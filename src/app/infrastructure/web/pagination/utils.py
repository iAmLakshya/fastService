from base64 import b64decode, b64encode
from binascii import Error as BinasciiError
from typing import Any

from app.infrastructure.constants import Pagination
from app.infrastructure.web.pagination.result import CursorResult, PageResult


def encode_cursor(value: str) -> str:
    return b64encode(value.encode()).decode()


def decode_cursor(cursor: str) -> str | None:
    try:
        return b64decode(cursor.encode()).decode()
    except (BinasciiError, UnicodeDecodeError, ValueError):
        return None


def paginate(
    items: list[Any],
    total: int,
    page: int,
    page_size: int,
) -> PageResult[Any]:
    return PageResult(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


def cursor_paginate(
    items: list[Any],
    limit: int,
    cursor_field: str = Pagination.DEFAULT_CURSOR_FIELD,
    prev_cursor_value: str | None = None,
) -> CursorResult[Any]:
    has_next = len(items) > limit
    if has_next:
        items = items[:limit]

    next_cursor = None
    if has_next and items:
        last_item = items[-1]
        if hasattr(last_item, cursor_field):
            next_cursor = encode_cursor(str(getattr(last_item, cursor_field)))
        elif isinstance(last_item, dict):
            next_cursor = encode_cursor(str(last_item.get(cursor_field, "")))

    prev_cursor = None
    if prev_cursor_value:
        prev_cursor = encode_cursor(prev_cursor_value)

    return CursorResult(
        items=items,
        next_cursor=next_cursor,
        prev_cursor=prev_cursor,
        has_next=has_next,
        has_prev=prev_cursor is not None,
    )
