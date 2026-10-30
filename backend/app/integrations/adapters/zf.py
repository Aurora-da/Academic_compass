from __future__ import annotations


class ZhiqiangAdapter:
    """M2 服务端代取（强智系）预留实现。

    合规前置：学校书面授权、最小字段集、凭据加密、频率限制。
    未取得授权时一律返回 not_configured，由前端降级到插件或文件导入。
    """

    name = "zhiqiang"

    async def fetch_plan(self, ctx: dict) -> dict:
        return self._not_configured()

    async def fetch_transcript(self, ctx: dict) -> dict:
        return self._not_configured()

    async def fetch_offerings(self, term: str, major: str) -> dict:
        return self._not_configured()

    async def fetch_enrollment(self, ctx: dict, term: str) -> dict:
        return self._not_configured()

    @staticmethod
    def _not_configured() -> dict:
        return {
            "error": "not_configured",
            "message": "服务端代取需要学校授权与 CAS 对接，当前未启用；请使用浏览器插件或文件导入。",
        }
