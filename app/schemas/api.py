from typing import Any, Optional

from pydantic import BaseModel


class ApiEnvelope(BaseModel):
    success: bool = True
    data: Optional[Any] = None
    message: str = ""
