from __future__ import annotations

from pydantic import BaseModel, Field

INTENT_PROMPT = """判断学生这句话的意图，并抽取槽位。

意图只能是：
- plan：查看培养方案、模块结构、课程要求、某门课在第几学期/考核方式
- audit：审核学分、差多少、能不能毕业、某模块缺口、第二课堂、挂科影响
- recommend：该选什么课、选课建议、方向怎么选、排课
- chat：其他关于规定的问答、寒暄、系统使用

槽位：
- semester：提到学期时抽取，形如 2025-2026-2
- course_code：提到课程编码时抽取，形如 B034913
- course_name：提到课程名时抽取
- direction：人工智能 / 嵌入式系统 / 算网融合
- simulate_course：如果问“如果挂了某门课会怎样”，填入课程名或编码

只输出 JSON，不要解释。
"""


class IntentResult(BaseModel):
    intent: str = Field(description="plan / audit / recommend / chat")
    semester: str | None = None
    course_code: str | None = None
    course_name: str | None = None
    direction: str | None = None
    simulate_course: str | None = None
    confidence: float = 0.8
