from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.models import (
    AuditSnapshot,
    Course,
    CoursePrerequisite,
    Enrollment,
    MappingDecision,
    Module,
    Offering,
    Plan,
    PlanCourse,
    PlanOverlay,
    SecondClassroomRecord,
    SecondClassroomReq,
    Student,
    User,
)
from app.services.plan.loader import compile_spec, load_plan_yaml, spec_hash
from app.services.plan.terms import academic_to_index, index_to_academic, term_index


def _read_json(name: str) -> dict:
    return json.loads((Path(settings.seed_dir) / name).read_text(encoding="utf-8"))


def _course_lookup(spec) -> dict[str, dict]:
    lookup: dict[str, dict] = {}

    def walk(module):
        for c in module.courses:
            lookup[c.code] = {
                "name": c.name,
                "credit": c.credit,
                "term": c.plan_term,
                "assessment": c.assessment,
                "nature": c.nature,
                "category": c.category,
                "tags": c.tags,
                "module": module.key,
            }
        for child in module.children:
            walk(child)

    for m in spec.modules:
        walk(m)
    return lookup


async def seed_plan(session: AsyncSession) -> Plan:
    spec = load_plan_yaml(settings.plan_path)
    existing = await session.get(Plan, spec.plan_id)
    if existing:
        return existing

    plan = Plan(
        id=spec.plan_id,
        name=spec.name,
        major=spec.major,
        major_code=spec.major_code,
        grade=spec.grade,
        degree=spec.degree,
        version="v1.2",
        total_credits=spec.total_credits,
        duration_json=spec.duration,
        graduation_conditions=spec.graduation_conditions,
        status=spec.status,
        source=spec.source,
        hash=spec_hash(settings.plan_path),
        effective_from=spec.effective_from,
    )
    session.add(plan)
    await session.flush()

    module_ids: dict[str, int] = {}
    order = 0

    async def add_module(module, parent_id: int | None):
        nonlocal order
        row = Module(  # noqa: F821
            plan_id=plan.id,
            parent_id=parent_id,
            key=module.key,
            name=module.name,
            mode=module.mode,
            require_credits=module.require,
            display_order=order,
            tag=module.tag,
            tags=module.tags,
            window_json=module.window,
            direction=module.direction,
        )
        order += 1
        session.add(row)
        await session.flush()
        module_ids[module.key] = row.id
        for course in module.courses:
            session.add(
                PlanCourse(
                    plan_id=plan.id,
                    module_id=row.id,
                    course_code=course.code,
                    name=course.name,
                    credit=course.credit,
                    plan_term=course.plan_term,
                    assessment=course.assessment,
                    nature=course.nature,
                    category=course.category,
                    tags=course.tags,
                )
            )
        for child in module.children:
            await add_module(child, row.id)

    for module in spec.modules:
        await add_module(module, None)

    # 课程主数据 + 统计（统计来自 offerings.json）
    offering_seed = _read_json("offerings.json")
    stats = offering_seed.get("course_stats", {})
    for code, info in _course_lookup(spec).items():
        session.add(
            Course(
                code=code,
                name=info["name"],
                name_norm=info["name"].lower().replace(" ", ""),
                credit=info["credit"],
                hours_json={
                    "lecture": round(info["credit"] * 16, 1),
                    "lab": 0,
                    "practice": 0,
                    "extra": 0,
                },
                nature=info["nature"],
                category=info["category"],
                tags=info["tags"],
                stats_json=stats.get(code, {}),
            )
        )

    for pre in spec.prerequisites:
        session.add(
            CoursePrerequisite(course_code=pre["course"], prereq_code=pre["prereq"], type=pre.get("type", "先修"))
        )

    for req in spec.second_classroom:
        session.add(
            SecondClassroomReq(
                plan_id=plan.id,
                category=req.category,
                period_type=req.period_type,
                min_count=req.min_count,
                label=req.label,
            )
        )

    await session.commit()
    return plan


async def seed_offerings(session: AsyncSession) -> None:
    existing = (await session.execute(select(Offering.id).limit(1))).first()
    if existing:
        return
    data = _read_json("offerings.json")
    for o in data["offerings"]:
        session.add(
            Offering(
                semester=o["semester"],
                course_code=o["course_code"],
                class_id=str(o["class_id"]),
                teacher=o.get("teacher", ""),
                time_slots=o.get("time_slots", []),
                capacity=o.get("capacity", 0),
                enrolled=o.get("enrolled", 0),
                allowed_grades=o.get("allowed_grades", []),
                campus=o.get("campus", "主校区"),
                note=o.get("note", ""),
            )
        )
    await session.commit()


def _synthetic_enrollments(student_seed: dict, courses: dict[str, dict]) -> list[dict]:
    cfg = student_seed["synthetic"]
    entry = student_seed["entry_year"]
    current_idx = academic_to_index(student_seed["current_term"], entry)
    direction_codes = set(cfg.get("direction_courses") or [])
    result: list[dict] = []
    for code, info in courses.items():
        idx = term_index(info["term"])
        if idx > current_idx:
            continue
        if info["module"].startswith("M5-") and code not in direction_codes:
            continue
        h = int(hashlib.sha256(f"{cfg['seed']}:{code}".encode()).hexdigest(), 16) % 1000 / 1000
        term = index_to_academic(idx, entry)
        if idx < current_idx:
            if h < cfg["passed_ratio"]:
                result.append(
                    {"code": code, "term": term, "status": "passed", "score": round(62 + (h * 1000) % 35, 1)}
                )
            elif h < cfg["passed_ratio"] + 0.05:
                result.append({"code": code, "term": term, "status": "failed", "score": round(40 + h * 30, 1)})
        else:
            if h < 0.45:
                result.append({"code": code, "term": term, "status": "studying"})
    return result


async def seed_students(session: AsyncSession, plan: Plan) -> None:
    existing = (await session.execute(select(Student.id).limit(1))).first()
    if existing:
        return

    spec = load_plan_yaml(settings.plan_path)
    courses = _course_lookup(spec)
    data = _read_json("students.json")
    admin = User(
        username="admin",
        password_hash=hash_password("123456"),
        display_name="教务管理员",
        role="admin",
    )
    session.add(admin)

    for seed in data["students"]:
        enrollments = seed.get("enrollments")
        if enrollments is None:
            enrollments = _synthetic_enrollments(seed, courses)
        student = Student(
            student_no=seed["student_no"],
            name=seed["name"],
            major=seed["major"],
            grade=seed["grade"],
            entry_year=seed["entry_year"],
            class_name=seed.get("class_name", ""),
            plan_id=plan.id,
            target_graduation_term=seed["target_graduation_term"],
            current_term=seed["current_term"],
            direction=seed.get("direction"),
            name_hash=hashlib.sha256(seed["name"].encode()).hexdigest(),
        )
        session.add(student)
        await session.flush()

        for e in enrollments:
            info = courses.get(e["code"], {})
            credit = info.get("credit", 0.0)
            session.add(
                Enrollment(
                    student_id=student.id,
                    course_code=e["code"],
                    course_name=info.get("name", ""),
                    term=e["term"],
                    status=e["status"],
                    score=e.get("score"),
                    gp=round(max(0.0, ((e.get("score") or 0) - 50) / 10), 2) if e.get("score") else None,
                    credits_earned=credit if e["status"] == "passed" else 0.0,
                    source="seed",
                )
            )

        for record in seed.get("second_classroom") or []:
            session.add(
                SecondClassroomRecord(
                    student_id=student.id,
                    category=record["category"],
                    term=record["term"],
                    date=record.get("date", ""),
                    title=record["title"],
                    evidence=record.get("evidence", ""),
                    status=record.get("status", "approved"),
                )
            )

        # 合成学生的第二课堂：王五有较完整记录，李四没有（展示“数据缺失”）
        if seed.get("synthetic") and seed["student_no"] == "2023002":
            for ay, cat, title in [
                ("2023-2024", "主题社会实践", "乡村支教社会实践"),
                ("2024-2025", "主题社会实践", "企业数字转型调研"),
                ("2023-2024", "创新实践", "大创项目总结报告"),
                ("2024-2025", "创新实践", "学科竞赛训练总结"),
                ("累 计", "学科竞赛与项目", "全国大学生计算机设计大赛国家级二等奖"),
                ("2025-2026", "学术交流研讨", "嵌入式系统前沿讲座"),
                ("2025-2026", "学术交流研讨", "CCF 系统软件技术论坛"),
            ]:
                term = "2025-2026-2" if cat == "学术交流研讨" else f"{ay}-2"
                session.add(
                    SecondClassroomRecord(
                        student_id=student.id,
                        category=cat,
                        term=term,
                        date="2026-03-01",
                        title=title,
                        status="approved",
                    )
                )

        for overlay in seed.get("overlays") or []:
            session.add(
                PlanOverlay(
                    student_id=student.id,
                    plan_id=plan.id,
                    type=overlay["type"],
                    payload_json=overlay["payload"],
                    approved_by=overlay.get("approved_by", ""),
                    effective_term=overlay.get("effective_term", seed["current_term"]),
                )
            )

        session.add(
            User(
                username=seed["student_no"],
                password_hash=hash_password("123456"),
                display_name=seed["name"],
                role="student",
                student_id=student.id,
            )
        )

    # 管理员端演示：低置信度映射队列 + 待审核第二课堂
    zhangsan = (
        await session.execute(select(Student).where(Student.student_no == "2023001"))
    ).scalar_one_or_none()
    if zhangsan:
        session.add(
            MappingDecision(
                raw_name="高等数学A(上)",
                raw_code="",
                course_code="B113101",
                confidence=0.78,
                method="L3",
                status="pending",
                context_json={"source": "示例成绩单", "candidates": ["B113101", "B113102"]},
            )
        )
        session.add(
            MappingDecision(
                raw_name="毛概",
                raw_code="",
                course_code="B881211",
                confidence=0.72,
                method="L3",
                status="pending",
                context_json={"source": "插件同步原始名称", "candidates": ["B881211"]},
            )
        )
        session.add(
            SecondClassroomRecord(
                student_id=zhangsan.id,
                category="学科竞赛与项目",
                term="2025-2026-2",
                date="2026-04-10",
                title="蓝桥杯省级二等奖（申请认定为国家级奖励，待审核）",
                evidence="获奖证书.pdf",
                status="pending",
            )
        )

    await session.commit()


async def seed_snapshots(session: AsyncSession) -> None:
    from app.services.audit.engine import run_audit

    existing = (await session.execute(select(AuditSnapshot.id).limit(1))).first()
    if existing:
        return
    student = (
        await session.execute(select(Student).where(Student.student_no == "2023001"))
    ).scalar_one_or_none()
    if not student:
        return
    for term in ("2024-2025-2", "2025-2026-2"):
        await run_audit(session, student, semester=term, save_snapshot=True)


async def seed_all(session: AsyncSession) -> None:
    plan = await seed_plan(session)
    await seed_offerings(session)
    await seed_students(session, plan)
    await seed_snapshots(session)


async def reset_and_seed(session: AsyncSession) -> None:
    from sqlalchemy import delete

    from app.core.db import Base

    for table in reversed(Base.metadata.sorted_tables):
        await session.execute(delete(table))
    await session.commit()
    await seed_all(session)
