from __future__ import annotations

from pathlib import Path

from docx import Document as DocxDocument

from app.services.ingestion.normalizer import normalize_row
from app.services.ingestion.pdf import _header_map


def parse_docx(path: str | Path, fallback_term: str = "") -> list[dict]:
    doc = DocxDocument(str(path))
    rows: list[dict] = []
    for table in doc.tables:
        data = [[cell.text.strip() for cell in row.cells] for row in table.rows]
        header_idx = None
        mapping = None
        for idx, row in enumerate(data[:5]):
            mapping = _header_map(row)
            if mapping:
                header_idx = idx
                break
        if mapping is None or header_idx is None:
            continue
        for row in data[header_idx + 1 :]:
            def get(field: str) -> str:
                idx = mapping.get(field)
                return row[idx] if idx is not None and idx < len(row) else ""

            if not get("name"):
                continue
            rows.append(
                normalize_row(
                    {
                        "name": get("name"),
                        "code": get("code"),
                        "credit": get("credit"),
                        "term": get("term") or fallback_term,
                        "status": get("status") or None,
                        "score": get("score") or None,
                        "nature": get("nature"),
                        "category": get("category"),
                    },
                    fallback_term,
                )
            )
    return [r for r in rows if r["raw_name"] and r["raw_credit"] is not None]
