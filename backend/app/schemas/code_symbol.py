from pydantic import BaseModel


class CodeSymbol(BaseModel):
    name: str
    type: str
    start_line: int
    end_line: int
