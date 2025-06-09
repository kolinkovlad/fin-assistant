from typing import Dict, Any

from pydantic import BaseModel


class ToolErrorResult(BaseModel):
    type: str = "tool_error"
    summary: str  # short human readable text
    payload: Dict[str, Any] = {}
