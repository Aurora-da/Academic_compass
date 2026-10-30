from __future__ import annotations

from datetime import datetime, timezone


class PluginAdapter:
    """M0 页面抓取：浏览器插件把 DOM 解析成 Canonical JSON，凭据不出本机。"""

    name = "plugin"

    async def fetch_transcript(self, ctx: dict) -> dict:
        courses = ctx.get("courses") or []
        return {
            "student": ctx.get("student") or {},
            "courses": courses,
            "meta": {
                "source": "plugin",
                "parsed_at": datetime.now(timezone.utc).isoformat(),
                "confidence": 0.99,
            },
        }

    async def fetch_plan(self, ctx: dict) -> dict:
        return {"plan": ctx.get("plan") or {}, "meta": {"source": "plugin"}}

    async def fetch_offerings(self, term: str, major: str) -> dict:
        return {"semester": term, "major": major, "offerings": []}

    async def fetch_enrollment(self, ctx: dict, term: str) -> dict:
        return {"semester": term, "courses": ctx.get("courses") or []}
