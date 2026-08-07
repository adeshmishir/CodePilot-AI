from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class CodeChunkModel(Base):
    __tablename__ = "code_chunks"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    repository_id: Mapped[int] = mapped_column(
        ForeignKey(
            "repositories.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    file_path: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    symbol_name: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    symbol_type: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    start_line: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    end_line: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
