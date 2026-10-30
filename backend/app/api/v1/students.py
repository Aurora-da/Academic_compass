from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_student
from app.core.config import settings
from app.core.db import get_db
from app.models import Enrollment, PlanOverlay, SecondClassroomRecord, Student
from app.schemas.api import DirectionRequest, SecondClassroomCreate, SimulateRequest
from app.services.audit.engine import get_diff, list_snapshots, run_audit
from app.services.audit.evaluator import simulate_failure
from app.services.audit.second_classroom import check_second_classroom
from app.services.plan.plan_service import load_runtime_plan, runtime_plan_dict
from app.services.planner.recommendation_service import build_recommendation

router = APIRouter(prefix="/students", tags=["students"])


@router.get("/me")
async def me(student: Student = Depends(get_current_student), db: AsyncSession = Depends(get_db)):
    plan = await load_runtime_plan(db, student.plan_id)
    enrollments = list(
        (await db.execute(select(Enrollment).where(Enrollment.student_id == student.id))).scalars().all()
    )
    return {
        "id": student.id,
        "student_no": student.student_no,
        "name": student.name,
        "major": student.major,
        "grade": student.grade,
        "entry_year": student.entry_year,
        "class_name": student.class_name,
        "current_term": student.current_term,
        "target_graduation_term": student.target_graduation_term,
        "direction": student.direction,
        "plan": {
            "id": plan.plan_id,
            "name": plan.name,
            "total_credits": plan.total_credits,
            "duration": plan.duration,
            "grade": plan.grade,
            "status": plan.status,
        },
        "enrollment_count": len(enrollments),
    }


@router.get("/me/audit")
async def audit(
    semester: str | None = Query(default=None),
    save: bool = Query(default=False),
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    report = await run_audit(db, student, semester=semester, save_snapshot=save)
    return report.to_dict()


@router.get("/me/recommend")
async def recommend(
    semester: str | None = Query(default=None),
    max_credits: float = Query(default=28.0, ge=10, le=40),
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    return await build_recommendation(db, student, semester=semester, max_credits=max_credits)


@router.post("/me/simulate")
async def simulate(
    payload: SimulateRequest,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    report = await run_audit(db, student, semester=payload.semester)
    plan = await load_runtime_plan(db, student.plan_id)
    result = simulate_failure(report, plan, payload.course_code)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/me/report")
async def report(
    semester: str | None = Query(default=None),
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    report_obj = await run_audit(db, student, semester=semester)
    plan = await load_runtime_plan(db, student.plan_id)
    records = list(
        (
            await db.execute(
                select(SecondClassroomRecord).where(SecondClassroomRecord.student_id == student.id)
            )
        )
        .scalars()
        .all()
    )
    diff = await get_diff(db, student.id)
    snapshots = await list_snapshots(db, student.id)
    sc = check_second_classroom(
        plan.second_classroom,
        [
            {
                "category": r.category,
                "term": r.term,
                "date": r.date,
                "title": r.title,
                "status": r.status,
            }
            for r in records
        ],
        student.entry_year,
        report_obj.as_of,
    )
    return {
        "audit": report_obj.to_dict(),
        "diff": diff,
        "second_classroom": sc,
        "snapshots": [
            {
                "id": s.id,
                "semester": s.semester,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "summary": (s.result_json or {}).get("summary"),
            }
            for s in snapshots
        ],
        "meta": {
            "engine_version": report_obj.engine_version,
            "generated_at": report_obj.generated_at,
            "disclaimer": "预演，以教务处终审为准",
        },
    }


@router.get("/me/snapshots")
async def snapshots(student: Student = Depends(get_current_student), db: AsyncSession = Depends(get_db)):
    rows = await list_snapshots(db, student.id)
    return [
        {
            "id": s.id,
            "semester": s.semester,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "summary": (s.result_json or {}).get("summary"),
            "graduation_ok": (s.result_json or {}).get("graduation", {}).get("ok"),
        }
        for s in rows
    ]


@router.get("/me/diff")
async def diff(
    from_term: str | None = Query(default=None),
    to_term: str | None = Query(default=None),
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    result = await get_diff(db, student.id, from_term, to_term)
    if result is None:
        return {"available": False, "message": "至少需要两个学期的快照才能对比"}
    return {"available": True, **result}


@router.get("/me/second-classroom")
async def second_classroom(
    student: Student = Depends(get_current_student), db: AsyncSession = Depends(get_db)
):
    plan = await load_runtime_plan(db, student.plan_id)
    records = list(
        (
            await db.execute(
                select(SecondClassroomRecord)
                .where(SecondClassroomRecord.student_id == student.id)
                .order_by(SecondClassroomRecord.term.desc())
            )
        )
        .scalars()
        .all()
    )
    rows = [
        {
            "id": r.id,
            "category": r.category,
            "term": r.term,
            "date": r.date,
            "title": r.title,
            "evidence": r.evidence,
            "status": r.status,
        }
        for r in records
    ]
    status = check_second_classroom(plan.second_classroom, rows, student.entry_year, student.current_term)
    return {
        "requirements": [s.__dict__ for s in plan.second_classroom],
        "items": status["items"],
        "ok": status["ok"],
        "status": status["status"],
        "records": rows,
        "current_term": student.current_term,
    }


@router.post("/me/second-classroom")
async def add_second_classroom(
    payload: SecondClassroomCreate,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    plan = await load_runtime_plan(db, student.plan_id)
    valid = {req.category for req in plan.second_classroom}
    if payload.category not in valid:
        raise HTTPException(status_code=400, detail=f"未知的第二课堂类别，可选：{', '.join(sorted(valid))}")
    record = SecondClassroomRecord(
        student_id=student.id,
        category=payload.category,
        term=payload.term or student.current_term,
        date=payload.date,
        title=payload.title,
        evidence=payload.evidence,
        status="pending",
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return {
        "id": record.id,
        "status": record.status,
        "message": "已提交，等待教学秘书审核后计入达标次数",
    }


@router.post("/me/direction")
async def lock_direction(
    payload: DirectionRequest,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    plan = await load_runtime_plan(db, student.plan_id)
    direction_node = plan.node(payload.direction_id)
    if direction_node is None or not direction_node.direction:
        raise HTTPException(status_code=404, detail="方向不存在")
    parent = next(
        (node for node in plan.walk() if any(c.key == payload.direction_id for c in node.children)),
        None,
    )
    if parent is None or parent.mode != "any_of":
        raise HTTPException(status_code=400, detail="该节点不是可选方向")
    student.direction = payload.direction_id
    existing = (
        await db.execute(
            select(PlanOverlay).where(
                PlanOverlay.student_id == student.id,
                PlanOverlay.type == "方向锁定",
            )
        )
    ).scalar_one_or_none()
    if existing:
        existing.payload_json = {"direction": payload.direction_id, "name": direction_node.name}
        existing.effective_term = student.current_term
    else:
        db.add(
            PlanOverlay(
                student_id=student.id,
                plan_id=student.plan_id,
                type="方向锁定",
                payload_json={"direction": payload.direction_id, "name": direction_node.name},
                approved_by="student",
                effective_term=student.current_term,
            )
        )
    await db.commit()
    return {
        "direction": payload.direction_id,
        "name": direction_node.name,
        "message": f"已锁定 {direction_node.name} 方向；审核与推荐将按该方向计算，并影响 2 学分创新实践选题",
    }


@router.get("/me/enrollments")
async def enrollments(student: Student = Depends(get_current_student), db: AsyncSession = Depends(get_db)):
    rows = list(
        (
            await db.execute(
                select(Enrollment)
                .where(Enrollment.student_id == student.id)
                .order_by(Enrollment.term.desc(), Enrollment.course_code)
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": r.id,
            "code": r.course_code,
            "name": r.course_name,
            "term": r.term,
            "status": r.status,
            "score": r.score,
            "gp": r.gp,
            "credits_earned": r.credits_earned,
        }
        for r in rows
    ]
