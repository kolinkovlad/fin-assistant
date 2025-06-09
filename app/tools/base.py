from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol, Any, Dict


class ToolResult(Protocol):
    summary: str  # always shown to the LLM / user
    payload: Dict[str, Any]  # tool-specific data (charts, numbers…)


class BaseTool(ABC):
    name: str
    description: str
    parameters: dict  # JSON-Schema compatible

    async def run(self, **kwargs) -> ToolResult: ...

    def openai_schema(self) -> dict:
        """
        Return the full tool spec expected by OpenAI’s `tools=` argument.
        """
        return {
            'type': 'function',
            'function': {
                'name': self.name,
                'description': self.description,
                'parameters': self.parameters,
            },
        }