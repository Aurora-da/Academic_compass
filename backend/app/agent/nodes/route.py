from __future__ import annotations

from app.agent.state import AgentState


def route(state: AgentState) -> str:
    if not state.get("guard_ok", False):
        return "chat"
    intent = state.get("intent", "chat")
    if intent in {"plan", "audit", "recommend"}:
        return intent
    return "chat"


def need_confirm(state: AgentState) -> str:
    return "confirm" if state.get("pending_confirm") else "verify"


def verify_ok(state: AgentState) -> str:
    verification = state.get("verification") or {}
    if verification.get("ok"):
        return "ok"
    if state.get("verification_attempts", 0) >= 2:
        # 最多重写 1 次；仍不一致则降级为模板输出
        return "ok"
    return "fail"
