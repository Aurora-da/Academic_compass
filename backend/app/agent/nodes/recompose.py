from __future__ import annotations

from app.agent.state import AgentState


async def recompose(state: AgentState) -> dict:
    """校验失败时只修数字事实，不让模型自由重写。最多重算 1 次。"""
    audit = state.get("audit")
    if audit:
        modules = audit.get("modules") or []
        summary = audit.get("summary") or {}
        earned = round(sum(min(m["earned"], m["require"]) for m in modules), 2)
        gap = round(sum(m["gap"] for m in modules), 2)
        summary["earned"] = earned
        summary["gap"] = gap
        summary["over"] = round(sum(m["over"] for m in modules), 2)
        summary["percent"] = round(earned / summary["require"] * 100, 2) if summary.get("require") else 0.0
        audit["summary"] = summary
        if audit.get("graduation", {}).get("credits"):
            audit["graduation"]["credits"].update({"earned": earned, "gap": gap})
        audit["summary"] = summary
        audit["modules"] = modules

    recommendation = state.get("recommendation")
    if recommendation:
        for plan in recommendation.get("plans") or []:
            plan["total_credits"] = round(sum(c["credit"] for c in plan.get("courses", [])), 2)

    return {
        "audit": audit,
        "recommendation": recommendation,
        "recompose_count": state.get("recompose_count", 0) + 1,
        "template_mode": True,
    }
