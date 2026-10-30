from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_student
from app.core.db import get_db
from app.models import Student
from app.services.planner.recommendation_service import build_recommendation

router = APIRouter(prefix="/recommend", tags=["recommend"])


@router.get("/me")
async def recommend_me(
    semester: str | None = Query(default=None),
    max_credits: float = Query(default=28.0, ge=10, le=40),
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    return await build_recommendation(db, student, semester=semester, max_credits=max_credits)
