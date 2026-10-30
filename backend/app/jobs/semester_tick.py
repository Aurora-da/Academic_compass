from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.logging import logger, setup_logging
from app.models import Student
from app.services.audit.engine import get_diff, list_snapshots, run_audit


async def semester_tick() -> dict:
    """学期巡检：重算快照、生成 diff，并把变化整理成推送文案（每学期 ≤4 条）。"""
    setup_logging()
    async with SessionLocal() as session:
        students = list((await session.execute(select(Student))).scalars().all())
        notifications = []
        for student in students:
            before = await list_snapshots(session, student.id)
            await run_audit(session, student, save_snapshot=True)
            diff = await get_diff(session, student.id)
            if diff:
                notifications.append(
                    {
                        "student_no": student.student_no,
                        "title": f"{student.name} · {diff['to']['semester']} 学业变化",
                        "body": diff["headline"],
                    }
                )
        logger.info("semester_tick: %s notifications", len(notifications))
        return {"notifications": notifications}


if __name__ == "__main__":
    asyncio.run(semester_tick())
