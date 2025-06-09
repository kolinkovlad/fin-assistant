from __future__ import annotations

from typing import List, Dict, Any
from datetime import datetime, timedelta

from pydantic import BaseModel

from .base import BaseTool
from .registry import register


class PerformanceResult(BaseModel):
    summary: str
    payload: dict


def _calc_period_return(
    transactions: List[Dict[str, Any]],
    latest_prices: Dict[str, float],
    since: datetime,
) -> float:
    """
    Toy time-weighted return calculator:
    • Assumes 'transactions' each have {'isin', 'quantity', 'price', 'timestamp'}
    • Ignores cash-flows after `since` to approximate TWR.
    """
    cost_basis, end_value = 0.0, 0.0
    for tx in transactions:
        if (ts := datetime.fromisoformat(tx['timestamp'])) < since:
            cost_basis += tx['quantity'] * tx['price']
            end_value += tx['quantity'] * latest_prices.get(tx['isin'], 0.0)
    if cost_basis == 0:
        return 0.0
    return round((end_value / cost_basis - 1) * 100, 2)  # %


class AnalyzePerformance(BaseTool):
    name = 'analyze_performance'
    description = 'Return time-period performance metrics and contribution by asset class'
    parameters = {
        'type': 'object',
        'properties': {},
        'required': [],
    }

    async def run(
        self,
        transactions: List[Dict[str, Any]],
        latest_prices: Dict[str, float],
        fund_metadata: List[Dict[str, Any]],
    ) -> PerformanceResult:
        today = datetime.utcnow()
        periods = {
            '1M': today - timedelta(days=30),
            '3M': today - timedelta(days=90),
            'YTD': datetime(today.year, 1, 1),
            '1Y': today - timedelta(days=365),
        }

        returns = {
            label: _calc_period_return(transactions, latest_prices, since)
            for label, since in periods.items()
        }

        # Crude contribution breakdown
        asset_class_map = {f['isin']: f.get('asset_class', 'other') for f in fund_metadata}
        contribution: Dict[str, float] = {}
        for tx in transactions:
            isin = tx['isin']
            asset_cls = asset_class_map.get(isin, 'other')
            qty = tx['quantity']
            gain = (latest_prices.get(isin, 0.0) - tx['price']) * qty
            contribution[asset_cls] = contribution.get(asset_cls, 0.0) + gain
        contribution = {k: round(v, 2) for k, v in contribution.items()}

        summary = (
            'Performance snapshot: '
            + ', '.join([f'{k}: {v:+.2f}%' for k, v in returns.items()])
        )

        payload = {
            'period_returns_%': returns,
            'asset_class_contribution_£': contribution,
        }
        return PerformanceResult(summary=summary, payload=payload)


register(AnalyzePerformance())