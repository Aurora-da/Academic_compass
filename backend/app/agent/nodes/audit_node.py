from __future__ import annotations

from app.agent.state import AgentState
from app.core.db import SessionLocal
from app.models import Student
from app.services.audit.engine import evaluate_prepared, prepare_audit, save_snapshot_payload
from app.services.plan.compiler import RuntimePlan
from app.agent.subgraphs.audit_graph import build_audit_subgraph

_AUDIT_SUBGRAPH = build_audit_subgraph()


def _resolve_course(plan: RuntimePlan, text: str | None) -> str | None:
    if not text:
        return None
    text = text.strip()
    for node in plan.walk():
        for course in node.courses:
            if course.code.lower() == text.lower() or course.name == text:
                return course.code
    for node in plan.walk():
        for course in node.courses:
            if text in course.name or course.name in text:
                return course.code
    return None


async def audit_node(state: AgentState) -> dict:
    async with SessionLocal() as session:
        student = await session.get(Student, int(state["student_id"]))
        if student is None:
            return {"errors": ["student_not_found"], "audit": None}
        semester = state.get("semester") or student.current_term
        prep = await prepare_audit(session, student, semester)

        sub_state = {
            "student_id": str(student.id),
            "semester": prep.current_term,
            "plan": prep.plan,
            "student": prep.student,
            "enrollments": prep.enrollments,
            "offerings": prep.offerings,
            "records": prep.records,
            "entry_year": prep.entry_year,
            "current_term": prep.current_term,
            "target_graduation_term": prep.target_graduation_term,
            "direction": prep.direction,
            "checks": [],
            "errors": [],
        }
        result = await _AUDIT_SUBGRAPH.ainvoke(sub_state)
        report = result["report"]

        simulation = None
        simulate_text = state.get("simulate_course")
        if not simulate_text and "挂" in (state.get("query") or ""):
            simulate_text = state.get("query")
        simulate_code = _resolve_course(prep.plan, simulate_text)
        if not simulate_code and "挂" in (state.get("query") or ""):
            simulate_code = _resolve_course(prep.plan, state.get("query"))
        if simulate_code:
            original = next((e for e in prep.enrollments if e["course_code"] == simulate_code), None)
            modified = []
            replaced = False
            for e in prep.enrollments:
                if e["course_code"] == simulate_code:
                    modified.append({**e, "status": "failed", "score": 45})
                    replaced = True
                else:
                    modified.append(e)
            if not replaced:
                modified.append(
                    {
                        "course_code": simulate_code,
                        "course_name": prep.plan.course_map().get(simulate_code).name,
                        "term": prep.current_term,
                        "status": "failed",
                        "score": 45,
                        "credit": prep.plan.course_map().get(simulate_code).credit,
                    }
                )
            after = evaluate_prepared(prep, modified)
            course = prep.plan.course_map().get(simulate_code)
            before_gap = report["summary"]["gap"]
            after_gap = after.summary["gap"]
            was_passed = bool(original and original.get("status") == "passed")
            if was_passed:
                verdict = (
                    f"如果《{course.name}》挂科，总缺口将从 {before_gap:.1f} 扩大到 {after_gap:.1f} 学分"
                )
            else:
                verdict = (
                    f"《{course.name}》当前尚未通过，挂科不会改变已获学分（缺口维持 {before_gap:.1f}）；"
                    f"但会占用本学期并顺延开课，按期毕业风险上升"
                )
            simulation = {
                "course": {
                    "code": simulate_code,
                    "name": course.name if course else simulate_code,
                    "credit": course.credit if course else 0,
                },
                "was_passed": was_passed,
                "summary_before": {"gap": before_gap, "earned": report["summary"]["earned"]},
                "summary_after": {"gap": after_gap, "earned": after.summary["earned"]},
                "gap_delta": round(after_gap - before_gap, 2),
                "module_changes": [
                    {
                        "id": m.key,
                        "name": m.name,
                        "gap_before": next((x["gap"] for x in report["modules"] if x["id"] == m.key), 0),
                        "gap_after": m.gap,
                        "ok_after": m.ok,
                    }
                    for m in after.modules
                    if m.gap != next((x["gap"] for x in report["modules"] if x["id"] == m.key), -1)
                ],
                "verdict": verdict,
            }

        await save_snapshot_payload(session, student, report, prep.current_term, report.get("engine_version", ""))

    return {
        "audit": report,
        "simulation": simulation,
        "pending_confirm": None,
        "errors": [],
    }
