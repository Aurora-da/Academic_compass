from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.db import get_db
from app.core.security import create_access_token, verify_password
from app.models import Student, User
from app.schemas.api import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_payload(user: User, student: Student | None) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "student": (
            {
                "id": student.id,
                "student_no": student.student_no,
                "name": student.name,
                "major": student.major,
                "grade": student.grade,
                "class_name": student.class_name,
                "current_term": student.current_term,
                "target_graduation_term": student.target_graduation_term,
                "plan_id": student.plan_id,
                "direction": student.direction,
            }
            if student
            else None
        ),
    }


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.username == payload.username))).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    student = await db.get(Student, user.student_id) if user.student_id else None
    token = create_access_token(str(user.id), user.role, {"username": user.username})
    return TokenResponse(access_token=token, user=_user_payload(user, student))


@router.get("/me")
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    student = await db.get(Student, user.student_id) if user.student_id else None
    return _user_payload(user, student)


@router.get("/demo-accounts")
async def demo_accounts(db: AsyncSession = Depends(get_db)):
    """演示账号（仅在 debug 模式暴露），方便评审快速体验。"""
    if not settings.debug:
        return {"accounts": []}
    users = list((await db.execute(select(User).order_by(User.id))).scalars().all())
    accounts = []
    for user in users:
        student = await db.get(Student, user.student_id) if user.student_id else None
        accounts.append(
            {
                "username": user.username,
                "password": "123456",
                "role": user.role,
                "display_name": user.display_name,
                "student_no": student.student_no if student else None,
                "grade": student.grade if student else None,
            }
        )
    return {"accounts": accounts}
