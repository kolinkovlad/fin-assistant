from typing import Dict, List

from pydantic import BaseModel

from app.tools.registry import all_tools   # ← NEW import

system_prompt = (
    "You are a helpful and precise financial assistant. "
    "When the user shares a financial goal (e.g., 'saving for a house in 3 years', "
    "'retiring in 20 years', or 'I want more aggressive growth'), "
    "you must map the goal to a suggested target allocation of asset classes (e.g. equities, bonds, cash), "
    "and call the 'rebalance_portfolio' tool with that target allocation. "
    "Only explain the recommendation after calling the tool. "
    "If the user does not provide a clear goal, ask them to clarify their investment objective. "
    "You can also use the 'find_fee_optimizations' tool to suggest lower-cost fund alternatives. "
    "Use the 'analyze_performance' tool to analyze recent portfolio performance, "
    "including time-based returns and asset-level contribution. "
    "Speak in plain English and avoid jargon. "
    "Never mention internal tool names or implementation details. "
    "Instead, explain insights, suggestions, or next steps in a friendly, helpful tone."
)


class RebalanceSuggestion(BaseModel):
    current_allocation: Dict[str, float]
    target_allocation: Dict[str, float]
    movements: List[str]

def get_tool_schema() -> list[dict]:
    """
    Return OpenAI-compatible schema definitions for every tool
    currently registered in the `app.tools` registry.

    Adding a new tool that calls `register()` is enough for it to
    show up here—no further edits required.
    """
    return [tool.openai_schema() for tool in all_tools().values()]