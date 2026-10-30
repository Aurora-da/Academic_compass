from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Module, Plan, PlanCourse, SecondClassroomReq, Student
from app.services.plan.compiler import RuntimeCourse, RuntimeNode, RuntimePlan, SecondClassroomSpec


class PlanNotFoundError(LookupError):
    pass


async def load_runtime_plan(session: AsyncSession, plan_id: str) -> RuntimePlan:
    plan = await session.get(Plan, plan_id)
    if plan is None:
        raise PlanNotFoundError(f"培养方案不存在：{plan_id}")
    modules = (
        (await session.execute(select(Module).where(Module.plan_id == plan_id).order_by(Module.display_order)))
        .scalars()
        .all()
    )
    plan_courses = (
        (await session.execute(select(PlanCourse).where(PlanCourse.plan_id == plan_id))).scalars().all()
    )
    by_module: dict[int, list[PlanCourse]] = {}
    for pc in plan_courses:
        by_module.setdefault(pc.module_id, []).append(pc)

    nodes: dict[int, RuntimeNode] = {}
    for m in modules:
        nodes[m.id] = RuntimeNode(
            key=m.key,
            name=m.name,
            mode=m.mode,  # type: ignore[arg-type]
            require=m.require_credits,
            tag=m.tag,
            tags=list(m.tags or []),
            window=m.window_json,
            direction=bool(m.direction),
        )
    roots: list[RuntimeNode] = []
    for m in modules:
        node = nodes[m.id]
        node.courses = [
            RuntimeCourse(
                code=pc.course_code,
                name=pc.name,
                credit=pc.credit,
                plan_term=pc.plan_term,
                assessment=pc.assessment,
                nature=pc.nature,
                category=pc.category,
                tags=list(pc.tags or []),
                module_key=m.key,
            )
            for pc in by_module.get(m.id, [])
        ]
        if m.parent_id and m.parent_id in nodes:
            nodes[m.parent_id].children.append(node)
        else:
            roots.append(node)

    reqs_rows = list(
        (
            await session.execute(
                select(SecondClassroomReq).where(SecondClassroomReq.plan_id == plan_id)
            )
        )
        .scalars()
        .all()
    )
    reqs = [
        SecondClassroomSpec(
            category=r.category, period_type=r.period_type, min_count=r.min_count, label=r.label
        )
        for r in reqs_rows
    ]
    return RuntimePlan(
        plan_id=plan.id,
        name=plan.name,
        major=plan.major,
        major_code=plan.major_code,
        grade=plan.grade,
        degree=plan.degree,
        total_credits=plan.total_credits,
        duration=dict(plan.duration_json or {}),
        status=plan.status,
        source=plan.source,
        effective_from=plan.effective_from,
        graduation_conditions=list(plan.graduation_conditions or []),
        roots=roots,
        second_classroom=reqs,
        prerequisites=[],
    )


async def get_student(session: AsyncSession, student_id: int) -> Student | None:
    return (await session.execute(select(Student).where(Student.id == student_id))).scalar_one_or_none()


async def get_student_by_no(session: AsyncSession, student_no: str) -> Student | None:
    return (
        (await session.execute(select(Student).where(Student.student_no == student_no))).scalar_one_or_none()
    )


async def list_students(session: AsyncSession, plan_id: str | None = None) -> list[Student]:
    stmt = select(Student)
    if plan_id:
        stmt = stmt.where(Student.plan_id == plan_id)
    return list((await session.execute(stmt.order_by(Student.student_no))).scalars().all())


async def get_plan_with_modules(session: AsyncSession, plan_id: str) -> Plan | None:
    return (
        await session.execute(
            select(Plan).where(Plan.id == plan_id).options(selectinload(Plan.modules), selectinload(Plan.courses))
        )
    ).scalar_one_or_none()


def runtime_plan_dict(plan: RuntimePlan, focus_course: dict | None = None) -> dict:
    def node_dict(node: RuntimeNode) -> dict:
        return {
            "id": node.key,
            "name": node.name,
            "mode": node.mode,
            "require": node.require,
            "tag": node.tag,
            "tags": node.tags,
            "window": node.window,
            "direction": node.direction,
            "courses": [
                {
                    "code": c.code,
                    "name": c.name,
                    "credit": c.credit,
                    "term": c.plan_term,
                    "assessment": c.assessment,
                    "nature": c.nature,
                    "category": c.category,
                    "tags": c.tags,
                }
                for c in node.courses
            ],
            "children": [node_dict(child) for child in node.children],
        }

    return {
        "id": plan.plan_id,
        "name": plan.name,
        "major": plan.major,
        "major_code": plan.major_code,
        "grade": plan.grade,
        "degree": plan.degree,
        "total_credits": plan.total_credits,
        "duration": plan.duration,
        "status": plan.status,
        "source": plan.source,
        "effective_from": plan.effective_from,
        "graduation_conditions": plan.graduation_conditions,
        "second_classroom": [s.__dict__ for s in plan.second_classroom],
        "modules": [node_dict(node) for node in plan.roots],
        "course_count": len(plan.course_map()),
        "focus_course": focus_course,
    }
