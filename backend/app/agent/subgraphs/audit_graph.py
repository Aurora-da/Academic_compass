from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agent.state import AuditGraphState
from app.services.audit.assigner import AssignCandidate, solve_assignment
from app.services.audit.evaluator import evaluate_plan
from app.services.audit.matcher import CourseMatcher
from app.services.plan.compiler import RuntimePlan


async def match_courses(state: AuditGraphState) -> dict:
    plan: RuntimePlan = state["plan"]
    course_list = [
        {"code": c.code, "name": c.name} for c in plan.course_map().values()
    ]
    matcher = CourseMatcher(course_list)
    matched: list[dict] = []
    for item in state.get("enrollments", []):
        result = matcher.match(item.get("course_name", ""), item.get("course_code", ""))
        matched.append(
            {
                "course_code": item.get("course_code"),
                "matched_code": result.course_code,
                "confidence": result.confidence,
                "method": result.method,
                "need_confirm": result.need_confirm,
            }
        )
    return {"matched": matched, "errors": list(state.get("errors") or [])}


async def assign_credits(state: AuditGraphState) -> dict:
    plan: RuntimePlan = state["plan"]
    course_map = plan.course_map()
    module_map = {node.key: node for node in plan.walk()}
    candidates: list[AssignCandidate] = []
    assignments: dict[str, str] = {}
    for code, course in course_map.items():
        modules = [node.key for node in plan.walk() if any(c.code == code for c in node.courses)]
        if len(modules) == 1:
            assignments[code] = modules[0]
        else:
            candidates.append(AssignCandidate(code=code, credit=course.credit, modules=modules))
    checks = list(state.get("checks") or [])
    if candidates:
        result = solve_assignment(
            candidates,
            [{"key": key, "require": node.require, "earned": 0} for key, node in module_map.items()],
            cap_at_require=False,
        )
        assignments.update(result["assignments"])
        checks.append({"type": "assignment", "solver": result["solver"], "count": len(result["assignments"])})
    return {"assignments": assignments, "checks": checks}


async def evaluate_tree(state: AuditGraphState) -> dict:
    plan: RuntimePlan = state["plan"]
    report = evaluate_plan(
        plan,
        state.get("enrollments", []),
        current_term=state["current_term"],
        entry_year=state["entry_year"],
        target_graduation_term=state.get("target_graduation_term", ""),
        direction=state.get("direction"),
        offerings=state.get("offerings", []),
        second_classroom_records=state.get("records", []),
        student=state.get("student", {}),
    )
    return {"report": report.to_dict()}


async def check_rules(state: AuditGraphState) -> dict:
    report = state["report"]
    modules = report["modules"]
    summary = report["summary"]
    checks = list(state.get("checks") or [])

    capped = round(sum(min(m["earned"], m["require"]) for m in modules), 2)
    gap = round(sum(m["gap"] for m in modules), 2)
    checks.append({"type": "credits_capped", "ok": abs(capped - summary["earned"]) < 1e-6, "value": capped})
    checks.append({"type": "gap_sum", "ok": abs(gap - summary["gap"]) < 1e-6, "value": gap})
    checks.append(
        {
            "type": "require_sum",
            "ok": abs(summary["earned"] + summary["gap"] - summary["require"]) < 1e-6,
            "value": summary["require"],
        }
    )
    structure_flags = [
        {"module": m["id"], "own_ok": m["own_ok"], "child_ok": m["child_ok"]}
        for m in modules
        if m["own_ok"] != m["child_ok"]
    ]
    checks.append({"type": "structure", "ok": True, "flags": structure_flags})
    return {"checks": checks}


def build_audit_subgraph():
    graph = StateGraph(AuditGraphState)
    graph.add_node("match", match_courses)
    graph.add_node("assign", assign_credits)
    graph.add_node("evaluate", evaluate_tree)
    graph.add_node("check", check_rules)
    graph.add_edge(START, "match")
    graph.add_edge("match", "assign")
    graph.add_edge("assign", "evaluate")
    graph.add_edge("evaluate", "check")
    graph.add_edge("check", END)
    return graph.compile()
