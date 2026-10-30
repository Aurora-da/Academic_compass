from __future__ import annotations

from app.agent.state import AgentState
from app.services.planner.filter import expand_slots


def _check_audit(audit: dict) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    warnings: list[str] = []
    modules = audit.get("modules") or []
    summary = audit.get("summary") or {}
    capped = round(sum(min(m["earned"], m["require"]) for m in modules), 2)
    if abs(capped - summary.get("earned", -1)) > 1e-6:
        issues.append(f"封顶后已获学分不一致：模块 {capped} vs 汇总 {summary.get('earned')}")
    gap_sum = round(sum(m["gap"] for m in modules), 2)
    if abs(gap_sum - summary.get("gap", -1)) > 1e-6:
        issues.append(f"缺口不一致：模块求和 {gap_sum} vs 汇总 {summary.get('gap')}")
    if abs(summary.get("earned", 0) + summary.get("gap", 0) - summary.get("require", 0)) > 1e-6:
        issues.append("已获 + 缺口 ≠ 要求学分")
    if abs(sum(m["require"] for m in modules) - summary.get("require", 0)) > 1e-6:
        issues.append("模块要求学分之和 ≠ 总学分")
    grad = audit.get("graduation") or {}
    credits = grad.get("credits") or {}
    if credits and abs(credits.get("earned", 0) - summary.get("earned", 0)) > 1e-6:
        issues.append("毕业条件中的已获学分与汇总不一致")
    if grad.get("second_classroom", {}).get("ok") is False:
        warnings.append("第二课堂存在未达标项")
    if not grad.get("thesis", {}).get("ok", False):
        warnings.append("毕业论文（设计）尚未通过")
    return issues, warnings


def _check_recommendation(rec: dict) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    warnings: list[str] = []
    current_credits = float(rec.get("current_credits") or 0)
    for plan in rec.get("plans") or []:
        codes = [c["code"] for c in plan.get("courses", [])]
        if len(codes) != len(set(codes)):
            issues.append(f"{plan['name']} 存在重复课程")
        total = round(sum(c["credit"] for c in plan.get("courses", [])), 2)
        if abs(total - plan.get("total_credits", 0)) > 1e-6:
            issues.append(f"{plan['name']} 学分合计不一致：{total} vs {plan.get('total_credits')}")
        if total + current_credits > plan.get("budget", 0) + 1e-6:
            issues.append(f"{plan['name']} 含在修学分后超出预算")
        taken: dict[str, str] = {}
        for course in plan.get("courses", []):
            for slot in expand_slots(course.get("slots") or []):
                if slot in taken:
                    issues.append(f"{plan['name']} 时间冲突：{course['name']} 与 {taken[slot]} 同在 {slot}")
                taken[slot] = course["name"]
        for course in plan.get("courses", []):
            if course.get("status") == "prereq_missing":
                issues.append(f"{course['name']} 先修未满足仍被推荐")
    sim = rec.get("feasibility") or {}
    if not sim.get("scenarios"):
        warnings.append("缺少毕业可行性情景")
    return issues, warnings


async def verify(state: AgentState) -> dict:
    issues: list[str] = []
    warnings: list[str] = []
    if state.get("audit"):
        i, w = _check_audit(state["audit"])
        issues += i
        warnings += w
    if state.get("recommendation"):
        i, w = _check_recommendation(state["recommendation"])
        issues += i
        warnings += w
    simulation = state.get("simulation")
    if simulation:
        delta = simulation["summary_after"]["gap"] - simulation["summary_before"]["gap"]
        if abs(delta - simulation["gap_delta"]) > 1e-6:
            issues.append("情景模拟缺口变化计算不一致")
    verification = {
        "ok": not issues,
        "issues": issues,
        "warnings": warnings,
        "attempt": state.get("verification_attempts", 0) + 1,
    }
    return {
        "verification": verification,
        "verification_attempts": state.get("verification_attempts", 0) + 1,
    }
