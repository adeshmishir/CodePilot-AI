from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class RepositoryManifestModel(Base):
    __tablename__ = "repository_manifest"
    __table_args__ = (
        UniqueConstraint(
            "repository_id", "file_path",
            name="uq_repository_manifest_repository_file"
        ),
    )

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

    size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    index_status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="indexed"
    )

    skip_reason: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    indexed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
