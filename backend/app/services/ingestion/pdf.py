from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

from app.services.ingestion.normalizer import normalize_row

HEADER_MAP = {
    "code": ("课程号", "课程编码", "课程代码", "课程编号", "编号"),
    "name": ("课程名称", "课程名", "名称"),
    "credit": ("学分",),
    "score": ("成绩", "总评", "分数", "得分"),
    "status": ("修读状态", "状态", "是否通过"),
    "term": ("学期", "学年学期", "开课学期"),
    "nature": ("课程性质", "修读要求"),
    "category": ("课程类别", "课程类型"),
}
CODE_RE = re.compile(r"[A-Za-z]\d{6}")


def _clean(value: str | None) -> str:
    return re.sub(r"\s+", "", str(value or ""))


def _header_map(row: list[str | None]) -> dict[str, int] | None:
    cells = [_clean(c) for c in row]
    mapping: dict[str, int] = {}
    for field, keywords in HEADER_MAP.items():
        for idx, cell in enumerate(cells):
            if any(k in cell for k in keywords):
                mapping[field] = idx
                break
    if "name" in mapping and "credit" in mapping:
        return mapping
    return None


def parse_pdf(path: str | Path, fallback_term: str = "") -> list[dict]:
    rows: list[dict] = []
    with pdfplumber.open(str(path)) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            try:
                tables = page.extract_tables()
            except Exception:
                continue
            for table in tables:
                header_idx = None
                mapping = None
                for idx, header in enumerate(table[:5]):
                    mapping = _header_map(header)
                    if mapping:
                        header_idx = idx
                        break
                if mapping is None or header_idx is None:
                    continue
                for row in table[header_idx + 1 :]:
                    if not row:
                        continue
                    cells = [_clean(c) for c in row]

                    def get(field: str) -> str:
                        idx = mapping.get(field)
                        return cells[idx] if idx is not None and idx < len(cells) else ""

                    name = get("name")
                    code = get("code")
                    if not name and not code:
                        continue
                    if "合计" in name or "小计" in name:
                        continue
                    if not code:
                        m = CODE_RE.search(" ".join(cells))
                        code = m.group(0) if m else ""
                    rows.append(
                        normalize_row(
                            {
                                "name": name,
                                "code": code,
                                "credit": get("credit") or None,
                                "term": get("term") or fallback_term,
                                "status": get("status") or None,
                                "score": get("score") or None,
                                "nature": get("nature"),
                                "category": get("category"),
                                "evidence": {"page": page_no},
                            },
                            fallback_term,
                        )
                    )
    return [r for r in rows if r["raw_name"] and r["raw_credit"] is not None]


def parse_pdf_text_blocks(path: str | Path, fallback_term: str = "") -> list[dict]:
    """没有表格线时的兜底：按行匹配“课程号 课程名 学分”。"""
    rows: list[dict] = []
    with pdfplumber.open(str(path)) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            for line in text.splitlines():
                m = CODE_RE.search(line)
                if not m:
                    continue
                rest = line[m.end() :].strip()
                credit = re.search(r"(\d+(?:\.\d+)?)\s*$", rest)
                if not credit:
                    continue
                name = rest[: credit.start()].strip()
                if len(name) < 2:
                    continue
                rows.append(
                    normalize_row(
                        {
                            "name": name,
                            "code": m.group(0),
                            "credit": credit.group(1),
                            "term": fallback_term,
                            "evidence": {"page": page_no},
                        },
                        fallback_term,
                    )
                )
    return rows
