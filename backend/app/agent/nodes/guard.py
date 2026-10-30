from __future__ import annotations

from sqlalchemy import func, select

from app.agent.state import AgentState
from app.core.db import SessionLocal
from app.models import Enrollment, Plan, Student


async def guard(state: AgentState) -> dict:
    """数据就绪检查：缺成绩/方案时转 chat 引导上传，而不是让模型硬答。"""
    errors: list[str] = []
    student_id = state.get("student_id")
    if not student_id:
        return {"guard_ok": False, "guard_reason": "未登录或缺少学生身份", "errors": ["no_student"]}

    async with SessionLocal() as session:
        student = await session.get(Student, int(student_id))
        if student is None:
            return {"guard_ok": False, "guard_reason": "学生档案不存在", "errors": ["student_not_found"]}
        plan = await session.get(Plan, student.plan_id)
        if plan is None:
            return {"guard_ok": False, "guard_reason": "未绑定培养方案", "errors": ["plan_not_found"]}
        count = (
            await session.execute(select(func.count(Enrollment.id)).where(Enrollment.student_id == student.id))
        ).scalar_one()

    profile = {
        "id": student.id,
        "student_no": student.student_no,
        "name": student.name,
        "major": student.major,
        "grade": student.grade,
        "entry_year": student.entry_year,
        "class_name": student.class_name,
        "plan_id": student.plan_id,
        "plan_name": plan.name,
        "plan_status": plan.status,
        "current_term": student.current_term,
        "target_graduation_term": student.target_graduation_term,
        "direction": student.direction,
        "enrollment_count": count,
    }
    if count == 0:
        return {
            "profile": profile,
            "guard_ok": False,
            "guard_reason": "还没有成绩数据，请先导入成绩单或使用插件同步",
            "errors": errors + ["no_enrollments"],
        }
    return {"profile": profile, "guard_ok": True, "guard_reason": None, "errors": errors}
