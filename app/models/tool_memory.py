from typing import Optional

from pydantic import BaseModel


class ToolCallRecord(BaseModel):
    tool_call_id: str
    name: str
    arguments: str  # JSON string
    content: str  # Result (as JSON string summary)
    summary: Optional[str] = None  # Summary of the tool call result
