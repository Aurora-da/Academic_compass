from __future__ import annotations

from sqlalchemy import select

from app.agent.state import AgentState
from app.core.db import SessionLocal
from app.models import CoursePrerequisite, Student
from app.services.plan.plan_service import load_runtime_plan


async def plan_node(state: AgentState) -> dict:
    async with SessionLocal() as session:
        student = await session.get(Student, int(state["student_id"]))
        if student is None:
            return {"errors": ["student_not_found"], "plan": None}
        plan = await load_runtime_plan(session, student.plan_id)
        prereqs = list((await session.execute(select(CoursePrerequisite))).scalars().all())

    query = state.get("query") or ""
    focus = None
    for node in plan.walk():
        for course in node.courses:
            if course.code in query or course.name in query:
                focus = {
                    "code": course.code,
                    "name": course.name,
                    "credit": course.credit,
                    "plan_term": course.plan_term,
                    "assessment": course.assessment,
                    "nature": course.nature,
                    "module": node.name,
                    "prerequisites": [
                        {"code": p.prereq_code, "type": p.type}
                        for p in prereqs
                        if p.course_code == course.code
                    ],
                }
                break
        if focus:
            break

    tree = [
        {
            "id": node.key,
            "name": node.name,
            "mode": node.mode,
            "require": node.require,
            "window": node.window,
            "courses": [
                {
                    "code": c.code,
                    "name": c.name,
                    "credit": c.credit,
                    "term": c.plan_term,
                    "assessment": c.assessment,
                    "nature": c.nature,
                }
                for c in node.courses
            ],
            "children": _tree(node.children),
        }
        for node in plan.roots
    ]
    return {
        "plan": {
            "id": plan.plan_id,
            "name": plan.name,
            "major": plan.major,
            "grade": plan.grade,
            "degree": plan.degree,
            "total_credits": plan.total_credits,
            "duration": plan.duration,
            "status": plan.status,
            "graduation_conditions": plan.graduation_conditions,
            "second_classroom": [s.__dict__ for s in plan.second_classroom],
            "modules": tree,
            "focus_course": focus,
            "course_count": len(plan.course_map()),
        }
    }


def _tree(nodes) -> list[dict]:
    return [
        {
            "id": node.key,
            "name": node.name,
            "mode": node.mode,
            "require": node.require,
            "window": node.window,
            "courses": [
                {
                    "code": c.code,
                    "name": c.name,
                    "credit": c.credit,
                    "term": c.plan_term,
                    "assessment": c.assessment,
                    "nature": c.nature,
                }
                for c in node.courses
            ],
            "children": _tree(node.children),
        }
        for node in nodes
    ]
