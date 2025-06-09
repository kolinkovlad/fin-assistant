from __future__ import annotations

import json
import logging
from typing import List, Dict, Any, Optional

from app import enums
from app.clients.openai_client import safe_chat_completion
from app.models.tool_memory import ToolCallRecord
from app.schema.goals import map_goal_to_allocation
from app.schema.tools import get_tool_schema, system_prompt
from app.server.schemes.chat import ChatResponse, Prompt
from app.services.history import ToolMemory, MessageHistory
from app.services.tool_dispatcher import ToolDispatcher  # ← thin registry-based
from app.tools.registry import get as get_tool  # for goal shortcuts
from app.tools.tool_errors import ToolErrorResult
from app.utils.token_estimate import count_tokens

logger = logging.getLogger(__name__)

MAX_HISTORY_TOKENS = 3_000


class LLMPortfolioAgent:
    """
    High-level orchestrator that:
      • builds conversational context
      • lets the LLM decide whether to call a tool
      • executes the tool (via ToolDispatcher)
      • feeds the result back to the LLM for the final answer
      • stores message + tool memory in Redis
    """

    def __init__(
            self,
            model: str,
            history: MessageHistory,
            memory: ToolMemory,
            holdings: list,
            cash_balances: list,
            fund_metadata: list,
            accounts: list,
            transactions: list,
            latest_prices: dict,
    ) -> None:
        self.model = model
        self.history = history
        self.memory = memory

        # domain context kept here so dispatcher can forward it to each tool
        self.tool_dispatcher = ToolDispatcher(
            holdings=holdings,
            cash_balances=cash_balances,
            fund_metadata=fund_metadata,
            accounts=accounts,
            transactions=transactions,
            latest_prices=latest_prices,
        )

        self.predefined_handler = PredefinedPromptHandler(
            agent=self, memory=memory, history=history
        )

    def set_model(self, model: enums.ModelName) -> None:
        self.model = model.value

    async def process_prompt(self, user_prompt: Prompt) -> ChatResponse:
        """
        Full turn handler:
          1. intercept “recap / why / reset / goal” commands
          2. send context + tool schemas to OpenAI
          3. (optional) run requested tool
          4. stream / return final content
        """
        # try hard-coded / goal-based shortcuts
        shortcut_resp = await self.predefined_handler.handle(user_prompt.text)
        if shortcut_resp:
            return shortcut_resp

        # build context & call LLM
        messages = await self._build_message_history(user_prompt.text)
        first = await safe_chat_completion(
            model=self.model,
            messages=messages,
            tools=get_tool_schema(),
            tool_choice='auto',
        )
        model_msg = first.choices[0].message
        tool_calls = getattr(model_msg, 'tool_calls', None)

        # store user prompt immediately
        await self.history.append({'role': 'user', 'content': user_prompt.text})

        # 3 ─ no tool requested → done
        if not tool_calls:
            await self.history.append({'role': 'assistant', 'content': model_msg.content})
            return ChatResponse(response=model_msg.content)

        # 3b ─ execute the first (only) tool call
        call = tool_calls[0]
        tool_result = await self.tool_dispatcher.dispatch(call)  # returns BaseModel
        result_dict = tool_result.model_dump()

        # custom post-processing examples
        if isinstance(tool_result, ToolErrorResult):
            polite = self._as_polite_reply(tool_result)
            await self.history.append({"role": "assistant", "content": polite})
            return ChatResponse(response=polite)
        if call.function.name == 'rebalance_portfolio':
            self._attach_allocation_summary(call, result_dict)
        elif call.function.name == 'analyze_performance':
            result_dict['performance_summary'] = result_dict.get('summary', '')

        # 4 ─ feed tool result back to LLM for the final answer
        final_resp = await self._respond_with_tool_result(call, result_dict)
        return final_resp

    async def _build_message_history(self, user_prompt: str) -> List[Dict[str, Any]]:
        """
        Combine: system prompt + persisted chat + (optional) last tool
        then trim to MAX_HISTORY_TOKENS.
        """
        base: List[Dict[str, Any]] = [
            {'role': 'system', 'content': system_prompt},
            *(await self.history.get()),
            {'role': 'user', 'content': user_prompt},
        ]

        if last := await self.memory.get_last():
            base.extend(
                [
                    {
                        'role': 'assistant',
                        'tool_calls': [
                            {
                                'id': last.tool_call_id,
                                'type': 'function',
                                'function': {
                                    'name': last.name,
                                    'arguments': last.arguments,
                                },
                            }
                        ],
                        'content': '',
                    },
                    {
                        'role': 'tool',
                        'tool_call_id': last.tool_call_id,
                        'name': last.name,
                        'content': last.content,
                    },
                ]
            )

        return await self._trim_to_token_limit(base)

    async def _trim_to_token_limit(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        total = 0
        kept = 0
        out: List[Dict[str, Any]] = []
        for msg in reversed(messages):
            tokens = count_tokens(json.dumps(msg), model=self.model)
            if total + tokens > MAX_HISTORY_TOKENS:
                break
            out.insert(0, msg)
            total += tokens
            kept += 1
        if kept < len(messages):
            logger.debug('Trimmed chat history to stay within token limit')
        return out

    async def _respond_with_tool_result(self, call_obj, result: Dict[str, Any]) -> ChatResponse:
        """
        Append the tool result as the required tool role message and call LLM
        again to craft user-facing answer, then persist history + memory.
        """
        follow_up = [
            {
                'role': 'assistant',
                'tool_calls': [
                    {
                        'id': call_obj.id,
                        'type': 'function',
                        'function': {
                            'name': call_obj.function.name,
                            'arguments': call_obj.function.arguments,
                        },
                    }
                ],
                'content': '',
            },
            {
                'role': 'tool',
                'tool_call_id': call_obj.id,
                'name': call_obj.function.name,
                'content': json.dumps(result),
            },
        ]

        msgs = await self._build_message_history('') + follow_up
        msgs = await self._trim_to_token_limit(msgs)

        second = await safe_chat_completion(model=self.model, messages=msgs)
        final_msg = second.choices[0].message.content

        # persist
        await self.history.append({'role': 'assistant', 'content': final_msg})
        await self.memory.set(
            [
                ToolCallRecord(
                    tool_call_id=call_obj.id,
                    name=call_obj.function.name,
                    arguments=call_obj.function.arguments,
                    content=json.dumps(result),
                    summary=result.get('summary') or final_msg,
                )
            ]
        )
        return ChatResponse(response=final_msg)

    def _attach_allocation_summary(self, call_obj, result: Dict[str, Any]) -> None:
        args = json.loads(call_obj.function.arguments)
        after_alloc = args.get('target_allocations')
        before_alloc = self.tool_dispatcher.get_allocation_breakdown()

        if after_alloc:
            result['allocation_summary'] = (
                    '\n📊 Current Allocation:\n'
                    + '\n'.join(f'- {k.capitalize()}: {v}%' for k, v in before_alloc.items())
                    + '\n\n🎯 Target Allocation:\n'
                    + '\n'.join(f'- {k.capitalize()}: {v}%' for k, v in after_alloc.items())
            )
        else:
            result['allocation_summary'] = (
                'No target allocation provided. '
                'Tell me your goal (e.g. “saving for a house in 3 years”) '
                'and I’ll suggest one!'
            )
    @staticmethod
    def _as_polite_reply(err: ToolErrorResult) -> str:
        missing = err.payload.get("missing", [])
        if "target_allocations" in missing:
            return (
                "Sure — I can rebalance your portfolio once I know your target allocation. "
                "You can either:\n"
                "• Tell me your percentages (e.g. “Equities 60 %, Bonds 30 %, Cash 10 %”), or\n"
                "• Describe your goal (e.g. “saving for a house in 3 years” or “retire in 20 years”).\n"
                "Let me know which works best!"
            )
        # fallback
        return "I’m missing some details to complete that action—could you provide them?"


class PredefinedPromptHandler:
    def __init__(self, agent: LLMPortfolioAgent, memory: ToolMemory, history: MessageHistory):
        self.agent = agent
        self.memory = memory
        self.history = history

    async def handle(self, user_input: str) -> Optional[ChatResponse]:
        lower = user_input.lower().strip()

        if lower in {'recap', 'give me a recap'}:
            return await self._recap()

        if lower in {'why', 'why?', 'explain'}:
            return await self._why()

        if lower in {'clear', 'reset'}:
            return await self._reset()

        # goal-triggered rebalance
        if target_alloc := map_goal_to_allocation(user_input):
            # call the tool directly (bypassing LLM) for a quick suggestion
            tool = get_tool('rebalance_portfolio')
            result = await tool.run(
                holdings=self.agent.tool_dispatcher.holdings,
                cash_accounts=self.agent.tool_dispatcher.cash_balances,
                fund_metadata=self.agent.tool_dispatcher.fund_metadata,
                target_allocations=target_alloc,
            )
            moves = '\n'.join(result.payload['movements'])
            return ChatResponse(
                response=(
                    'Based on your goal, here’s what I suggest:\n\n'
                    '🔄 Rebalancing Actions:\n'
                    f'{moves}\n\n{result.payload["allocation_summary"]}'
                )
            )

        return None

    async def _recap(self) -> ChatResponse:
        records = await self.memory.get_all()
        if not records:
            return ChatResponse(response='There’s nothing to recap yet.')
        bullets = '\n'.join(f'- {r.summary or r.content}' for r in records)
        return ChatResponse(response='Here’s a recap of what we’ve done:\n' + bullets)

    async def _why(self) -> ChatResponse:
        last = await self.memory.get_last()
        if not last:
            return ChatResponse(response='I don’t have any previous actions to explain.')
        return ChatResponse(response=last.summary or last.content)

    async def _reset(self) -> ChatResponse:
        await self.memory.clear()
        await self.history.clear()
        return ChatResponse(response='Alright, I’ve cleared the session. Let’s start fresh!')
