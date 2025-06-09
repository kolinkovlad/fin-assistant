from __future__ import annotations

from typing import List, Dict, Any

from pydantic import BaseModel

from .base import BaseTool
from .registry import register

FEE_THRESHOLD_BPS = 5  # 0.05 %
ALIASES = {
    'equity - developed markets': 'equity - global',  # treat SWDA vs VWRL as same bucket
}


class FeeOptimizationResult(BaseModel):
    summary: str
    payload: dict


class FindFeeOptimizations(BaseTool):
    name = 'find_fee_optimizations'
    description = 'Identify cheaper funds or share classes with equivalent exposure'
    parameters = {
        'type': 'object',
        'properties': {},
        'required': [],
    }

    async def run(
            self,
            holdings: List[Dict[str, Any]],
            fund_metadata: List[Dict[str, Any]],
    ) -> FeeOptimizationResult:
        isin_map = {f['isin']: f for f in fund_metadata}

        suggestions: List[str] = []
        total_estimated_savings = 0.0

        for h in holdings:
            isin = h['isin']
            value = h['value']
            cur_fund = isin_map.get(isin)
            if not cur_fund:
                continue

            cur_fee = cur_fund.get('ongoing_charge', 0)  # % p.a.
            asset_class = ALIASES.get(cur_fund['asset_class'].lower(), cur_fund['asset_class'].lower())

            # look for cheaper alternative in same bucket
            cheaper = min(
                (
                    f for f in fund_metadata
                    if f.get('asset_class') == asset_class
                       and f.get('ongoing_charge', 100) < cur_fee
                ),
                key=lambda f: f['ongoing_charge'],
                default=None,
            )

            if cheaper and (cur_fee - cheaper['ongoing_charge']) * 100 >= FEE_THRESHOLD_BPS:
                delta_fee = cur_fee - cheaper['ongoing_charge']
                annual_saving = round(value * delta_fee / 100, 2)
                total_estimated_savings += annual_saving

                suggestions.append(
                    f'- Switch **{cur_fund["name"]}** ({cur_fee:.2%}) → **{cheaper["name"]}** '
                    f'({cheaper["ongoing_charge"]:.2%}) | save ≈ £{annual_saving:.2f}/yr'
                )

        if suggestions:
            summary = f'Found {len(suggestions)} cheaper alternatives ' \
                      f'worth ≈ £{total_estimated_savings:.2f} in annual savings.'
        else:
            summary = 'No fee optimizations found.'

        payload = {
            'suggestions': suggestions,
            'total_estimated_savings': total_estimated_savings,
        }
        return FeeOptimizationResult(summary=summary, payload=payload)


register(FindFeeOptimizations())
