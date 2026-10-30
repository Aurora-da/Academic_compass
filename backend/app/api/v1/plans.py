from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models import Plan
from app.services.plan.loader import load_plan_yaml
from app.services.plan.plan_service import load_runtime_plan, runtime_plan_dict
from app.services.plan.validator import validate_spec
from app.core.config import settings

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("")
async def list_plans(db: AsyncSession = Depends(get_db)):
    rows = list((await db.execute(select(Plan).order_by(Plan.grade.desc()))).scalars().all())
    return [
        {
            "id": p.id,
            "name": p.name,
            "major": p.major,
            "major_code": p.major_code,
            "grade": p.grade,
            "degree": p.degree,
            "total_credits": p.total_credits,
            "duration": p.duration_json,
            "status": p.status,
            "source": p.source,
        }
        for p in rows
    ]


@router.get("/{plan_id}/validation")
async def validation(plan_id: str, db: AsyncSession = Depends(get_db)):
    plan_row = await db.get(Plan, plan_id)
    if plan_row is None:
        raise HTTPException(status_code=404, detail="培养方案不存在")
    spec = load_plan_yaml(settings.plan_path)
    issues = validate_spec(spec)
    return {
        "plan_id": plan_id,
        "status": plan_row.status,
        "hash": plan_row.hash,
        "issues": [i.to_dict() for i in issues],
        "errors": len([i for i in issues if i.level == "error"]),
        "warnings": len([i for i in issues if i.level == "warning"]),
    }


@router.get("/{plan_id}")
async def get_plan_by_id(
    plan_id: str,
    q: str | None = Query(default=None, description="聚焦某门课程（编码或名称）"),
    db: AsyncSession = Depends(get_db),
):
    plan_row = await db.get(Plan, plan_id)
    if plan_row is None:
        raise HTTPException(status_code=404, detail="培养方案不存在")
    plan = await load_runtime_plan(db, plan_row.id)
    focus = None
    if q:
        for node in plan.walk():
            for course in node.courses:
                if q in course.code or q in course.name or course.name in q:
                    focus = {
                        "code": course.code,
                        "name": course.name,
                        "credit": course.credit,
                        "plan_term": course.plan_term,
                        "assessment": course.assessment,
                        "nature": course.nature,
                        "module": node.name,
                    }
                    break
            if focus:
                break
    return runtime_plan_dict(plan, focus)


@router.get("/{major}/{grade}")
async def get_plan(
    major: str,
    grade: int,
    q: str | None = Query(default=None, description="聚焦某门课程（编码或名称）"),
    db: AsyncSession = Depends(get_db),
):
    plan_row = await db.get(Plan, major)
    if plan_row is None:
        plan_row = (
            await db.execute(
                select(Plan).where(
                    Plan.grade == grade,
                    or_(Plan.major_code == major, Plan.major.like(f"%{major}%")),
                )
            )
        ).scalars().first()
    if plan_row is None:
        raise HTTPException(status_code=404, detail="培养方案不存在")
    plan = await load_runtime_plan(db, plan_row.id)
    focus = None
    if q:
        for node in plan.walk():
            for course in node.courses:
                if q in course.code or q in course.name or course.name in q:
                    focus = {
                        "code": course.code,
                        "name": course.name,
                        "credit": course.credit,
                        "plan_term": course.plan_term,
                        "assessment": course.assessment,
                        "nature": course.nature,
                        "module": node.name,
                    }
                    break
            if focus:
                break
    return runtime_plan_dict(plan, focus)
