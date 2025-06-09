# app/services/tool_dispatcher.py
from __future__ import annotations

import inspect
import json
from typing import Any, Dict

from app.tools.rebalance_portfolio import ASSET_CLASS_BUCKETS  # for allocation breakdown
from app.tools.registry import get as get_tool
from app.tools.tool_errors import ToolErrorResult


class ToolDispatcher:
    """
    Thin adapter around the tool registry.

    • Injects shared domain context (holdings, cash, prices, …) into every call.
    • Filters kwargs so each tool only receives the parameters it expects.
    • Provides a helper for quick “current allocation” breakdown.
    """

    def __init__(
            self,
            *,
            holdings: list,
            cash_balances: list,
            fund_metadata: list,
            accounts: list,
            transactions: list,
            latest_prices: dict,
    ) -> None:
        self._ctx: Dict[str, Any] = {
            'holdings': holdings,
            'cash_accounts': cash_balances,
            'cash_balances': cash_balances,
            'fund_metadata': fund_metadata,
            'accounts': accounts,
            'transactions': transactions,
            'latest_prices': latest_prices,
        }

    def __getattr__(self, name: str) -> Any:
        """
        Let callers access dispatcher.holdings, dispatcher.cash_balances, …
        without exposing the private _ctx dict.
        """
        try:
            return self._ctx[name]
        except KeyError:
            raise AttributeError(name) from None

    async def dispatch(self, tool_call) -> Any:
        """
        Execute the tool requested by the model.

        Parameters
        ----------
        tool_call : openai.types.chat.ChatCompletionMessageToolCall
            Object from the OpenAI response (contains .function.{name, arguments})

        Returns
        -------
        Pydantic model (ToolResult)
        """

        name = tool_call.function.name
        explicit = json.loads(tool_call.function.arguments or '{}')
        tool = get_tool(name)

        sig = inspect.signature(tool.run)
        required = [p for p, v in sig.parameters.items() if v.default is inspect._empty]
        missing = [p for p in required if p not in explicit and p not in self._ctx]

        if missing:
            # graceful fall-back
            return ToolErrorResult(
                summary="missing_arguments",
                payload={"missing": missing},
            )

        kwargs = {k: v for k, v in {**self._ctx, **explicit}.items() if k in sig.parameters}
        return await tool.run(**kwargs)

    def get_allocation_breakdown(self) -> Dict[str, float]:
        """
        Return current % allocation (equities / bonds / cash / other) for quick summaries.
        """
        holdings = self._ctx['holdings']
        cash_accounts = self._ctx['cash_balances']
        fund_metadata = self._ctx['fund_metadata']

        isin_map = {f['isin']: f for f in fund_metadata}

        totals: Dict[str, float] = {}
        for h in holdings:
            isin = h['isin']
            value = h['value']
            raw_class = isin_map.get(isin, {}).get('asset_class', 'other')
            bucket = ASSET_CLASS_BUCKETS.get(raw_class.lower(), 'other')
            totals[bucket] = totals.get(bucket, 0) + value

        cash_total = sum(acct['balance'] for acct in cash_accounts)
        portfolio_value = sum(totals.values()) + cash_total

        allocation_pct = {
            k: round(v / portfolio_value * 100, 2) for k, v in totals.items()
        }
        allocation_pct['cash'] = round(cash_total / portfolio_value * 100, 2)
        return allocation_pct
