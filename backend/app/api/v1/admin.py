from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.db import get_db
from app.models import (
    AuditSnapshot,
    Course,
    CourseAlias,
    MappingDecision,
    Offering,
    Plan,
    SecondClassroomRecord,
    Student,
    User,
)
from app.schemas.api import MappingConfirmRequest, SecondClassroomReview, TrialRequest
from app.services.audit.engine import run_audit
from app.services.plan.loader import load_plan_yaml
from app.services.plan.validator import validate_spec
from app.core.config import settings

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard")
async def dashboard(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    students = list((await db.execute(select(Student).order_by(Student.student_no))).scalars().all())
    rows = []
    module_acc: dict[str, dict] = {}
    risk_count = 0
    for student in students:
        report = await run_audit(db, student)
        summary = report.summary
        at_risk = summary["gap"] > 0 or report.graduation["second_classroom"]["ok"] is not True
        if at_risk:
            risk_count += 1
        rows.append(
            {
                "id": student.id,
                "student_no": student.student_no,
                "name": student.name,
                "grade": student.grade,
                "class_name": student.class_name,
                "earned": summary["earned"],
                "gap": summary["gap"],
                "percent": summary["percent"],
                "studying": summary["studying"],
                "graduation_ok": report.graduation["ok"],
                "credits_ok": report.graduation["credits"]["ok"],
                "second_classroom_ok": report.graduation["second_classroom"]["ok"],
                "thesis_ok": report.graduation["thesis"]["ok"],
                "risk_count": len(report.risks),
                "top_risk": (report.risks[0]["msg"] if report.risks else ""),
            }
        )
        for module in report.modules:
            acc = module_acc.setdefault(
                module.key,
                {
                    "id": module.key,
                    "name": module.name,
                    "require": module.require,
                    "earned_sum": 0.0,
                    "gap_sum": 0.0,
                    "below": 0,
                },
            )
            acc["earned_sum"] += module.earned
            acc["gap_sum"] += module.gap
            if not module.ok:
                acc["below"] += 1

    module_rows = []
    for acc in module_acc.values():
        n = max(1, len(students))
        module_rows.append(
            {
                "id": acc["id"],
                "name": acc["name"],
                "require": acc["require"],
                "avg_earned": round(acc["earned_sum"] / n, 2),
                "avg_gap": round(acc["gap_sum"] / n, 2),
                "students_below": acc["below"],
                "total": len(students),
            }
        )

    pending_mappings = (
        await db.execute(
            select(MappingDecision).where(MappingDecision.status == "pending").limit(20)
        )
    ).scalars().all()
    pending_sc = (
        await db.execute(
            select(SecondClassroomRecord).where(SecondClassroomRecord.status == "pending").limit(20)
        )
    ).scalars().all()

    return {
        "summary": {
            "students": len(students),
            "avg_percent": round(sum(r["percent"] for r in rows) / max(1, len(rows)), 2),
            "at_risk": risk_count,
            "graduated_ready": sum(1 for r in rows if r["graduation_ok"]),
            "pending_mappings": len(pending_mappings),
            "pending_second_classroom": len(pending_sc),
        },
        "plan": (
            {
                "id": plan_row.id,
                "hash": plan_row.hash,
                "status": plan_row.status,
                "name": plan_row.name,
            }
            if (plan_row := (await db.execute(select(Plan).limit(1))).scalars().first())
            else None
        ),
        "students": rows,
        "modules": module_rows,
        "pending_second_classroom": [
            {
                "id": r.id,
                "student_id": r.student_id,
                "category": r.category,
                "term": r.term,
                "title": r.title,
                "date": r.date,
                "status": r.status,
            }
            for r in pending_sc
        ],
    }


@router.get("/mappings")
async def mappings(
    status: str = Query(default="pending"),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = list(
        (
            await db.execute(
                select(MappingDecision)
                .where(MappingDecision.status == status)
                .order_by(MappingDecision.created_at.desc())
                .limit(100)
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": r.id,
            "raw_name": r.raw_name,
            "raw_code": r.raw_code,
            "course_code": r.course_code,
            "confidence": r.confidence,
            "method": r.method,
            "status": r.status,
            "context": r.context_json,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.post("/mappings/{mapping_id}/confirm")
async def confirm_mapping(
    mapping_id: int,
    payload: MappingConfirmRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(MappingDecision, mapping_id)
    if row is None:
        raise HTTPException(status_code=404, detail="映射记录不存在")
    course = await db.get(Course, payload.course_code)
    if course is None:
        raise HTTPException(status_code=404, detail="目标课程不存在")
    row.course_code = payload.course_code
    row.status = "confirmed"
    row.confidence = 1.0
    row.method = "manual"
    row.confirmed_by = user.display_name
    if payload.create_alias:
        exists = (
            await db.execute(
                select(CourseAlias).where(
                    CourseAlias.alias_norm == row.raw_name.lower().replace(" ", ""),
                    CourseAlias.course_code == payload.course_code,
                )
            )
        ).scalar_one_or_none()
        if not exists:
            db.add(
                CourseAlias(
                    alias=row.raw_name,
                    alias_norm=row.raw_name.lower().replace(" ", ""),
                    course_code=payload.course_code,
                    source="admin",
                )
            )
    await db.commit()
    return {"id": row.id, "status": row.status, "course_code": row.course_code}


@router.get("/second-classroom")
async def second_classroom_queue(
    status: str = Query(default="pending"),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = list(
        (
            await db.execute(
                select(SecondClassroomRecord)
                .where(SecondClassroomRecord.status == status)
                .order_by(SecondClassroomRecord.created_at.desc())
                .limit(100)
            )
        )
        .scalars()
        .all()
    )
    students = {
        s.id: s for s in (await db.execute(select(Student))).scalars().all()
    }
    return [
        {
            "id": r.id,
            "student_no": students[r.student_id].student_no if r.student_id in students else "",
            "student_name": students[r.student_id].name if r.student_id in students else "",
            "category": r.category,
            "term": r.term,
            "date": r.date,
            "title": r.title,
            "evidence": r.evidence,
            "status": r.status,
        }
        for r in rows
    ]


@router.post("/second-classroom/{record_id}/review")
async def review_second_classroom(
    record_id: int,
    payload: SecondClassroomReview,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(SecondClassroomRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    record.status = payload.status
    record.evidence = (record.evidence + f" | 审核意见：{payload.comment}") if payload.comment else record.evidence
    await db.commit()
    return {"id": record.id, "status": record.status}


@router.get("/plans")
async def admin_plans(_: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    plans = list((await db.execute(select(Plan))).scalars().all())
    return [
        {
            "id": p.id,
            "name": p.name,
            "grade": p.grade,
            "status": p.status,
            "total_credits": p.total_credits,
            "hash": p.hash,
            "source": p.source,
        }
        for p in plans
    ]


@router.post("/plans/{plan_id}/trial")
async def trial(
    plan_id: str,
    payload: TrialRequest,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.get(Plan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="培养方案不存在")
    stmt = select(Student).where(Student.plan_id == plan_id)
    if payload.student_nos:
        stmt = stmt.where(Student.student_no.in_(payload.student_nos))
    students = list((await db.execute(stmt)).scalars().all())
    results = []
    for student in students:
        report = await run_audit(db, student)
        snapshot = (
            await db.execute(
                select(AuditSnapshot)
                .where(
                    AuditSnapshot.student_id == student.id,
                    AuditSnapshot.plan_id == plan_id,
                    AuditSnapshot.semester == report.as_of,
                )
                .order_by(AuditSnapshot.created_at.desc())
            )
        ).scalars().first()
        expected = ((snapshot.result_json or {}).get("summary") if snapshot else None)
        actual = report.summary
        consistent = None
        if expected:
            consistent = (
                abs(expected.get("earned", -1) - actual["earned"]) < 1e-6
                and abs(expected.get("gap", -1) - actual["gap"]) < 1e-6
            )
        results.append(
            {
                "student_no": student.student_no,
                "name": student.name,
                "actual": actual,
                "expected": expected,
                "consistent": consistent,
                "modules": [
                    {"id": m.key, "require": m.require, "earned": m.earned, "gap": m.gap}
                    for m in report.modules
                ],
            }
        )
    return {
        "plan_id": plan_id,
        "students": results,
        "all_consistent": bool(results) and all(r["consistent"] is True for r in results),
        "note": "正式发布前需与教务系统“要求/获得/未获得”三列逐项对齐",
    }


@router.post("/plans/{plan_id}/publish")
async def publish_plan(
    plan_id: str,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.get(Plan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="培养方案不存在")
    spec = load_plan_yaml(settings.plan_path)
    issues = validate_spec(spec)
    errors = [i.to_dict() for i in issues if i.level == "error"]
    if errors:
        raise HTTPException(status_code=400, detail={"message": "方案一致性校验未通过", "errors": errors})
    plan.status = "frozen"
    await db.commit()
    return {"id": plan.id, "status": plan.status, "issues": [i.to_dict() for i in issues]}


@router.get("/offerings")
async def offerings(
    semester: str | None = Query(default=None),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Offering)
    if semester:
        stmt = stmt.where(Offering.semester == semester)
    rows = list((await db.execute(stmt.order_by(Offering.semester, Offering.course_code))).scalars().all())
    courses = {c.code: c.name for c in (await db.execute(select(Course))).scalars().all()}
    return [
        {
            "id": o.id,
            "semester": o.semester,
            "course_code": o.course_code,
            "course_name": courses.get(o.course_code, ""),
            "class_id": o.class_id,
            "teacher": o.teacher,
            "time_slots": o.time_slots,
            "capacity": o.capacity,
            "enrolled": o.enrolled,
            "note": o.note,
        }
        for o in rows
    ]
