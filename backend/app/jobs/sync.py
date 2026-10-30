from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.logging import logger, setup_logging
from app.models import Plan, Student
from app.services.audit.engine import run_audit
from app.services.plan.plan_service import load_runtime_plan


async def refresh_snapshots() -> dict:
    """每学期/每次成绩更新后重算全部学生快照，供 diff 与推送使用。"""
    setup_logging()
    async with SessionLocal() as session:
        students = list((await session.execute(select(Student))).scalars().all())
        plans = {p.id for p in (await session.execute(select(Plan))).scalars().all()}
        done = 0
        for student in students:
            if student.plan_id not in plans:
                continue
            await load_runtime_plan(session, student.plan_id)
            await run_audit(session, student, save_snapshot=True)
            done += 1
        logger.info("refresh_snapshots: %s students", done)
        return {"students": done}


if __name__ == "__main__":
    asyncio.run(refresh_snapshots())
