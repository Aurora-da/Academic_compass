from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_student
from app.core.db import get_db
from app.models import Student
from app.schemas.api import SimulateRequest
from app.services.audit.engine import run_audit
from app.services.audit.evaluator import simulate_failure
from app.services.plan.plan_service import load_runtime_plan

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/me")
async def audit_me(
    semester: str | None = Query(default=None),
    save: bool = Query(default=False),
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    report = await run_audit(db, student, semester=semester, save_snapshot=save)
    return report.to_dict()


@router.post("/simulate")
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
