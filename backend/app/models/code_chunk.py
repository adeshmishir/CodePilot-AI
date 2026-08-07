from sqlalchemy import Column, Integer, String, Text

from app.database.base import Base


class CodeChunkModel(Base):
    __tablename__ = "code_chunks"

    id = Column(Integer, primary_key=True, index=True)

    file_path = Column(String, nullable=False)

    symbol_name = Column(String, nullable=False)

    symbol_type = Column(String, nullable=False)

    start_line = Column(Integer, nullable=False)

    end_line = Column(Integer, nullable=False)

    content = Column(Text, nullable=False)
