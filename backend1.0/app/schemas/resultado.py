from typing import Any

from pydantic import BaseModel


class CalculoResponse(BaseModel):
    tipo: str
    resultado: dict[str, Any]