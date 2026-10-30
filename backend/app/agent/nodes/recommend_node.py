from __future__ import annotations

from app.agent.state import AgentState
from app.core.db import SessionLocal
from app.models import Student
from app.services.planner.recommendation_service import build_recommendation


async def recommend_node(state: AgentState) -> dict:
    async with SessionLocal() as session:
        student = await session.get(Student, int(state["student_id"]))
        if student is None:
            return {"errors": ["student_not_found"], "recommendation": None}
        recommendation = await build_recommendation(
            session, student, semester=state.get("semester") or student.current_term
        )
    return {"recommendation": recommendation, "errors": []}
