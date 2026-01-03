from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure import Base, TimestampMixin, UUIDMixin


class Todo(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "todos"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
