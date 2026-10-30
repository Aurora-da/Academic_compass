from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import AuditSnapshot, Enrollment, Offering, PlanOverlay, SecondClassroomRecord, Student
from app.services.audit.evaluator import AuditReport, evaluate_plan
from app.services.plan.compiler import RuntimePlan
from app.services.plan.plan_service import load_runtime_plan


class AuditError(RuntimeError):
    pass


@dataclass
class AuditPreparation:
    plan: RuntimePlan
    student: dict
    enrollments: list[dict]
    offerings: list[dict]
    records: list[dict]
    student_id: int
    entry_year: int
    current_term: str
    target_graduation_term: str
    direction: str | None


async def _enrollments_as_dict(session: AsyncSession, student_id: int, as_of: str | None) -> list[dict]:
    stmt = select(Enrollment).where(Enrollment.student_id == student_id)
    if as_of:
        stmt = stmt.where(Enrollment.term <= as_of)
    rows = list((await session.execute(stmt)).scalars().all())
    return [
        {
            "course_code": e.course_code,
            "course_name": e.course_name,
            "term": e.term,
            "status": e.status,
            "score": e.score,
            "gp": e.gp,
            "credit": e.credits_earned,
        }
        for e in rows
    ]


async def _offerings_as_dict(session: AsyncSession) -> list[dict]:
    rows = list((await session.execute(select(Offering))).scalars().all())
    return [
        {
            "semester": o.semester,
            "course_code": o.course_code,
            "class_id": o.class_id,
            "teacher": o.teacher,
            "time_slots": list(o.time_slots or []),
            "capacity": o.capacity,
            "enrolled": o.enrolled,
            "allowed_grades": list(o.allowed_grades or []),
            "campus": o.campus,
            "note": o.note,
        }
        for o in rows
    ]


async def _records_as_dict(session: AsyncSession, student_id: int) -> list[dict]:
    rows = list(
        (await session.execute(select(SecondClassroomRecord).where(SecondClassroomRecord.student_id == student_id)))
        .scalars()
        .all()
    )
    return [
        {
            "category": r.category,
            "term": r.term,
            "date": r.date,
            "title": r.title,
            "status": r.status,
            "evidence": r.evidence,
        }
        for r in rows
    ]


async def _student_dict(session: AsyncSession, student: Student) -> dict:
    overlays = list(
        (await session.execute(select(PlanOverlay).where(PlanOverlay.student_id == student.id))).scalars().all()
    )
    return {
        "id": student.id,
        "student_no": student.student_no,
        "name": student.name,
        "major": student.major,
        "grade": student.grade,
        "entry_year": student.entry_year,
        "class_name": student.class_name,
        "plan_id": student.plan_id,
        "current_term": student.current_term or settings.current_term,
        "target_graduation_term": student.target_graduation_term,
        "direction": student.direction,
        "overlays": [
            {
                "type": o.type,
                "payload": o.payload_json,
                "approved_by": o.approved_by,
                "effective_term": o.effective_term,
            }
            for o in overlays
        ],
    }


async def prepare_audit(
    session: AsyncSession, student: Student, semester: str | None = None
) -> AuditPreparation:
    as_of = semester or student.current_term or settings.current_term
    plan = await load_runtime_plan(session, student.plan_id)
    enrollments = await _enrollments_as_dict(session, student.id, as_of)
    offerings = await _offerings_as_dict(session)
    records = await _records_as_dict(session, student.id)
    student_info = await _student_dict(session, student)
    direction = student.direction
    if not direction:
        for overlay in student_info["overlays"]:
            if overlay["type"] == "方向锁定":
                direction = (overlay.get("payload") or {}).get("direction") or direction
    return AuditPreparation(
        plan=plan,
        student=student_info,
        enrollments=enrollments,
        offerings=offerings,
        records=records,
        student_id=student.id,
        entry_year=student.entry_year,
        current_term=as_of,
        target_graduation_term=student.target_graduation_term,
        direction=direction,
    )


def evaluate_prepared(
    prep: AuditPreparation, enrollments: list[dict] | None = None
) -> AuditReport:
    """Evaluate a prepared audit, optionally replacing the enrollment snapshot.

    The agent's what-if simulation reuses the plan/offerings/records prepared once
    and only swaps enrollments, avoiding another full database read.
    """
    return evaluate_plan(
        prep.plan,
        prep.enrollments if enrollments is None else enrollments,
        current_term=prep.current_term,
        entry_year=prep.entry_year,
        target_graduation_term=prep.target_graduation_term,
        direction=prep.direction,
        offerings=prep.offerings,
        second_classroom_records=prep.records,
        student=prep.student,
    )


async def run_audit(
    session: AsyncSession,
    student: Student,
    *,
    semester: str | None = None,
    save_snapshot: bool = False,
) -> AuditReport:
    prep = await prepare_audit(session, student, semester)
    report = evaluate_prepared(prep)
    if save_snapshot:
        await save_audit_snapshot(session, student, report)
    return report


async def save_audit_snapshot(session: AsyncSession, student: Student, report: AuditReport) -> AuditSnapshot:
    return await save_snapshot_payload(session, student, report.to_dict(), report.as_of, report.engine_version)


async def save_snapshot_payload(
    session: AsyncSession,
    student: Student,
    payload: dict[str, Any],
    semester: str,
    engine_version: str = "",
) -> AuditSnapshot:
    existing = (
        await session.execute(
            select(AuditSnapshot).where(
                AuditSnapshot.student_id == student.id,
                AuditSnapshot.semester == semester,
                AuditSnapshot.plan_id == student.plan_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        existing.result_json = payload
        existing.engine_version = engine_version or settings.engine_version
        existing.created_at = datetime.now(timezone.utc)
        await session.commit()
        return existing
    snapshot = AuditSnapshot(
        student_id=student.id,
        semester=semester,
        plan_id=student.plan_id,
        result_json=payload,
        engine_version=engine_version or settings.engine_version,
    )
    session.add(snapshot)
    await session.commit()
    await session.refresh(snapshot)
    return snapshot


async def list_snapshots(session: AsyncSession, student_id: int, limit: int = 12) -> list[AuditSnapshot]:
    return list(
        (
            await session.execute(
                select(AuditSnapshot)
                .where(AuditSnapshot.student_id == student_id)
                .order_by(AuditSnapshot.semester)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )


def diff_snapshots(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    prev_codes = {c["code"]: c for c in previous.get("passed_courses", [])}
    curr_codes = {c["code"]: c for c in current.get("passed_courses", [])}
    new_codes = [c for code, c in curr_codes.items() if code not in prev_codes]
    new_credits = round(sum(c.get("credit", 0) for c in new_codes), 2)

    def modules_of(report: dict) -> dict[str, dict]:
        return {m["id"]: m for m in report.get("modules", [])}

    prev_modules, curr_modules = modules_of(previous), modules_of(current)
    module_changes = []
    for key, cur in curr_modules.items():
        prev = prev_modules.get(key)
        if not prev:
            continue
        if abs(cur["earned"] - prev["earned"]) > 1e-9 or cur["ok"] != prev["ok"]:
            module_changes.append(
                {
                    "id": key,
                    "name": cur["name"],
                    "earned_before": prev["earned"],
                    "earned_after": cur["earned"],
                    "gap_before": prev["gap"],
                    "gap_after": cur["gap"],
                    "ok_before": prev["ok"],
                    "ok_after": cur["ok"],
                    "status": cur["status"],
                }
            )

    prev_sc = {i["category"] + i["period_label"]: i for i in previous.get("graduation", {}).get("second_classroom", {}).get("items", [])}
    curr_sc = {i["category"] + i["period_label"]: i for i in current.get("graduation", {}).get("second_classroom", {}).get("items", [])}
    sc_changes = []
    for key, cur in curr_sc.items():
        prev = prev_sc.get(key)
        if prev and prev["status"] != cur["status"]:
            sc_changes.append({"key": key, "before": prev["status"], "after": cur["status"], "message": cur["message"]})

    prev_risks = {r["msg"] for r in previous.get("risks", [])}
    new_risks = [r for r in current.get("risks", []) if r["msg"] not in prev_risks]

    gap_before = previous["summary"]["gap"]
    gap_after = current["summary"]["gap"]
    delta = round(gap_after - gap_before, 2)
    headline = (
        f"新增通过 {len(new_codes)} 门课程 / +{new_credits:.1f} 学分；"
        f"缺口 {gap_before:.1f} → {gap_after:.1f}（{'缩小' if delta < 0 else '扩大'} {abs(delta):.1f}）"
    )
    return {
        "from": {"semester": previous.get("as_of"), "gap": gap_before, "earned": previous["summary"]["earned"]},
        "to": {"semester": current.get("as_of"), "gap": gap_after, "earned": current["summary"]["earned"]},
        "headline": headline,
        "new_passed": new_codes,
        "new_passed_count": len(new_codes),
        "new_passed_credits": new_credits,
        "module_changes": module_changes,
        "second_classroom_changes": sc_changes,
        "new_risks": new_risks,
    }


async def get_diff(
    session: AsyncSession, student_id: int, from_term: str | None = None, to_term: str | None = None
) -> dict[str, Any] | None:
    snapshots = await list_snapshots(session, student_id)
    if len(snapshots) < 2:
        return None
    by_term = {s.semester: s for s in snapshots}
    if to_term and to_term in by_term:
        current = by_term[to_term]
    else:
        current = snapshots[-1]
    if from_term and from_term in by_term:
        previous = by_term[from_term]
    else:
        previous = next((s for s in reversed(snapshots) if s.semester < current.semester), snapshots[0])
    if previous.semester == current.semester:
        return None
    return diff_snapshots(previous.result_json, current.result_json)


async def clear_snapshots(session: AsyncSession, student_id: int) -> None:
    await session.execute(delete(AuditSnapshot).where(AuditSnapshot.student_id == student_id))
    await session.commit()
