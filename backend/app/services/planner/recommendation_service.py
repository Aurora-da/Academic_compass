from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Course, CoursePrerequisite, Student
from app.services.audit.engine import evaluate_prepared, prepare_audit
from app.services.planner.direction import compare_directions
from app.services.planner.feasibility import assess_feasibility
from app.services.planner.filter import build_candidates, expand_slots
from app.services.planner.scorer import score_candidates
from app.services.planner.solver import solve_plans


async def build_recommendation(
    session: AsyncSession,
    student: Student,
    *,
    semester: str | None = None,
    max_credits: float = 28.0,
) -> dict:
    term = semester or student.current_term or settings.current_term
    prep = await prepare_audit(session, student, term)
    report = evaluate_prepared(prep)
    plan = prep.plan
    offerings = prep.offerings

    prereq_rows = (
        await session.execute(
            select(CoursePrerequisite.course_code, CoursePrerequisite.prereq_code, CoursePrerequisite.type)
        )
    ).all()
    prerequisites = [
        {"course": course_code, "prereq_code": prereq_code, "type": kind}
        for course_code, prereq_code, kind in prereq_rows
    ]
    stats = {
        code: dict(stats_json or {})
        for code, stats_json in (
            await session.execute(select(Course.code, Course.stats_json))
        ).all()
    }

    current_offerings: dict[str, list[dict]] = {}
    future_map: dict[str, list[str]] = {}
    for o in offerings:
        if o["semester"] == term:
            current_offerings.setdefault(o["course_code"], []).append(o)
        elif o["semester"] > term:
            future_map.setdefault(o["course_code"], []).append(o["semester"])

    locked_courses = []
    seen_locked: set[str] = set()
    for m in report.modules:
        for c in m.studying_courses:
            code = c["code"]
            if code in seen_locked:
                continue
            seen_locked.add(code)
            offs = current_offerings.get(code, [])
            locked_courses.append(
                {
                    "code": code,
                    "name": c["name"],
                    "credit": c["credit"],
                    "slots": offs[0]["time_slots"] if offs else [],
                }
            )

    candidates, blocked = build_candidates(
        plan,
        report,
        offerings,
        prerequisites,
        current_term=term,
        grade=student.grade,
        locked_codes={c["code"] for c in locked_courses},
        direction=student.direction,
    )

    current_offerings_count = {code: len(rows) for code, rows in current_offerings.items()}
    for cand in candidates + blocked:
        cand.offering_count = current_offerings_count.get(cand.code, 0)
        cand.future_semesters = sorted(set(future_map.get(cand.code, [])))
        cand.difficulty = stats.get(cand.code, {})

    scored = score_candidates(
        candidates,
        plan,
        report,
        prerequisites,
        current_term=term,
        entry_year=student.entry_year,
        target_term=student.target_graduation_term,
        direction=student.direction,
    )
    plans = solve_plans(scored, locked_courses=locked_courses, current_credits=report.summary["studying"])
    feasibility = assess_feasibility(
        plan,
        report,
        offerings,
        entry_year=student.entry_year,
        current_term=term,
        max_credits=max_credits,
    )
    direction = compare_directions(
        plan, report, offerings, current_term=term, locked_courses=locked_courses
    )

    return {
        "semester": term,
        "student": {
            "student_no": student.student_no,
            "name": student.name,
            "grade": student.grade,
            "direction": student.direction,
        },
        "summary": report.summary,
        "audit": report.to_dict(),
        "candidates": [c.to_dict() for c in scored],
        "blocked": [c.to_dict() for c in blocked],
        "plans": [p.to_dict() for p in plans],
        "locked_courses": locked_courses,
        "current_credits": report.summary["studying"],
        "direction_comparison": direction,
        "feasibility": feasibility,
        "notes": [
            "推荐以当学期开课计划（offering）为硬约束，培养方案指导性学期只作先验。",
            "所有学分与缺口数字由审核引擎计算，模型只负责解释。",
            "结果为预演，最终以教务处终审为准。",
        ],
    }
