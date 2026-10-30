from __future__ import annotations

from langgraph.types import interrupt

from app.agent.state import AgentState


async def confirm_mapping(state: AgentState) -> dict:
    """低置信度映射/课程认定需要人工确认时挂起，前端回填后沿回边重算。"""
    pending = state.get("pending_confirm")
    if not pending:
        return {}
    answer = interrupt(pending)
    return {
        "pending_confirm": None,
        "confirmation": answer if isinstance(answer, dict) else {"answer": answer},
    }
