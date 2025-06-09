from typing import List, Dict, Any

from pydantic import BaseModel

from .base import BaseTool
from .registry import register

ASSET_CLASS_BUCKETS = {
    'equity - us': 'equities',
    'equity - global': 'equities',
    'equity - developed markets': 'equities',
    'bond - global aggregate': 'bonds',
    'bond - short term': 'bonds',
    'cash': 'cash'
}


class RebalancePortfolioResult(BaseModel):
    summary: str
    payload: dict


class RebalancePortfolio(BaseTool):
    name = 'rebalance_portfolio'
    description = 'Rebalance holdings toward new target allocations'
    parameters = {
        'type': 'object',
        'properties': {
            'target_allocations': {
                'type': 'object',
                'description': 'Dict of asset class → % target',
            }
        },
        'required': ['target_allocations'],
    }

    async def run(
            self,
            holdings: List[Dict[str, Any]],
            cash_accounts: List[Dict[str, Any]],
            fund_metadata: List[Dict[str, Any]],
            target_allocations: Dict[str, float],
    ) -> RebalancePortfolioResult:
        isin_map = {f['isin']: f for f in fund_metadata}

        asset_class_totals = {}
        holding_details = []

        for h in holdings:
            isin = h['isin']
            value = h['value']
            raw_class = isin_map.get(isin, {}).get('asset_class', 'other')
            asset_class = ASSET_CLASS_BUCKETS.get(raw_class.lower(), 'other')
            asset_class_totals[asset_class] = asset_class_totals.get(asset_class, 0) + value
            holding_details.append({**h, 'asset_class': asset_class})

        total_cash = sum(c['balance'] for c in cash_accounts)
        total_value = sum(asset_class_totals.values()) + total_cash

        current_allocation = {
            k: round(v / total_value * 100, 2) for k, v in asset_class_totals.items()
        }
        current_allocation['cash'] = round(total_cash / total_value * 100, 2)

        # Delta calculation
        allocation_deltas = {}
        all_assets = set(target_allocations) | set(current_allocation)
        for asset in all_assets:
            current_pct = current_allocation.get(asset, 0)
            target_pct = target_allocations.get(asset, 0)
            delta_pct = target_pct - current_pct
            delta_value = round(total_value * delta_pct / 100, 2)
            allocation_deltas[asset] = delta_value

        # Suggestion categories
        sells, reallocs, invests = [], [], []
        available_cash = total_cash

        for asset, delta in allocation_deltas.items():
            if abs(delta) < 1:
                continue

            if delta < 0:
                sells.append(f"- Reduce exposure to {asset} by £{-delta:.2f}.")
            else:
                fund = find_fund_for_asset_class(asset, fund_metadata)
                name = fund['name'] if fund else f"{asset} fund"

                from_cash = min(delta, available_cash)
                if from_cash > 0:
                    invests.append(f"- Invest £{from_cash:.2f} into {name} ({asset})")
                    available_cash -= from_cash

                remaining = delta - from_cash
                if remaining > 0:
                    reallocs.append(f"- Reallocate £{remaining:.2f} to {asset}.")

        # Combine sections
        suggestions = []
        if sells:
            suggestions.append("🔻 **Sell / Reduce Exposure:**\n" + "\n".join(sells))
        if reallocs:
            suggestions.append("🔄 **Reallocate from Surplus Holdings:**\n" + "\n".join(reallocs))
        if invests:
            suggestions.append("💰 **Invest Available Cash:**\n" + "\n".join(invests))

        allocation_summary = (
                "\n📊 Current Allocation:\n" +
                "\n".join([f"- {k.capitalize()}: {v}%" for k, v in current_allocation.items()]) +
                "\n\n🎯 Target Allocation:\n" +
                "\n".join([f"- {k.capitalize()}: {v}%" for k, v in target_allocations.items()])
        )

        payload = {
            "current_allocation": current_allocation,
            "target_allocations": target_allocations,
            "movements": suggestions,
            "allocation_summary": allocation_summary
        }
        return RebalancePortfolioResult(summary=allocation_summary, payload=payload)


register(RebalancePortfolio())


def find_fund_for_asset_class(asset_class: str, fund_metadata: List[Dict[str, Any]]) -> Dict[str, Any]:
    for fund in fund_metadata:
        if fund.get('bucket') == asset_class:
            return fund
    return {}
