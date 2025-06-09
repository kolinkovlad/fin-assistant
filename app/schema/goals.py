from typing import Dict

GOAL_ALLOCATION_MAP: Dict[str, Dict[str, float]] = {
    "saving_for_house": {
        "equities": 20,
        "bonds": 40,
        "cash": 40
    },
    "retirement": {
        "equities": 60,
        "bonds": 30,
        "cash": 10
    },
    "short_term_savings": {
        "equities": 10,
        "bonds": 40,
        "cash": 50
    }
}



def map_goal_to_allocation(user_input: str) -> Dict[str, float] | None:
    lower = user_input.lower()
    if "house" in lower:
        return GOAL_ALLOCATION_MAP["saving_for_house"]
    if "retire" in lower:
        return GOAL_ALLOCATION_MAP["retirement"]
    if "vacation" in lower or "travel" in lower or "short term" in lower:
        return GOAL_ALLOCATION_MAP["short_term_savings"]
    return None
