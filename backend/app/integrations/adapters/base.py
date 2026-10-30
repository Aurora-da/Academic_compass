from __future__ import annotations

from typing import Protocol


class AcademicAdapter(Protocol):
    """四级接入的抽象：换一所学校 = 新增 Adapter + 一份方案数据，不换引擎。"""

    name: str

    async def fetch_plan(self, ctx: dict) -> dict: ...

    async def fetch_transcript(self, ctx: dict) -> dict: ...

    async def fetch_offerings(self, term: str, major: str) -> dict: ...

    async def fetch_enrollment(self, ctx: dict, term: str) -> dict: ...
