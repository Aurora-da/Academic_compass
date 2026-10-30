from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

from langchain_core.documents import Document

from app.core.config import settings

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]")


def _tokenize(text: str) -> list[str]:
    chars = _TOKEN_RE.findall(text.lower())
    bigrams = [chars[i] + chars[i + 1] for i in range(len(chars) - 1)]
    return chars + bigrams


@dataclass
class KnowledgeChunk:
    doc: Document
    tokens: list[str]
    term_freq: dict[str, int]
    length: int


class BM25Retriever:
    def __init__(self, docs: list[Document], k1: float = 1.5, b: float = 0.75):
        self.docs = docs
        self.k1 = k1
        self.b = b
        self.chunks = [
            KnowledgeChunk(d, _tokenize(d.page_content), {}, 0) for d in docs
        ]
        self.df: dict[str, int] = {}
        for chunk in self.chunks:
            counts: dict[str, int] = {}
            for token in chunk.tokens:
                counts[token] = counts.get(token, 0) + 1
            chunk.term_freq = counts
            chunk.length = len(chunk.tokens)
            for token in counts:
                self.df[token] = self.df.get(token, 0) + 1
        self.avg_len = sum(c.length for c in self.chunks) / max(1, len(self.chunks))
        self.N = len(self.chunks)

    def search(self, query: str, k: int = 4) -> list[tuple[Document, float]]:
        q_tokens = _tokenize(query)
        scores: list[tuple[Document, float]] = []
        for chunk in self.chunks:
            score = 0.0
            for token in q_tokens:
                tf = chunk.term_freq.get(token, 0)
                if tf == 0:
                    continue
                df = self.df.get(token, 0)
                idf = math.log(1 + (self.N - df + 0.5) / (df + 0.5))
                denom = tf + self.k1 * (1 - self.b + self.b * chunk.length / max(1e-9, self.avg_len))
                score += idf * tf * (self.k1 + 1) / denom
            if score > 0:
                scores.append((chunk.doc, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]


def _load_regulations() -> list[Document]:
    path = Path(settings.seed_dir).parent / "knowledge" / "regulations.md"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    docs: list[Document] = []
    for block in text.split("\n## "):
        block = block.strip()
        if not block:
            continue
        if block.startswith("# "):
            continue
        title, _, body = block.partition("\n")
        content = f"{title.strip()}\n{body.strip()}".strip()
        if len(content) < 30:
            continue
        docs.append(
            Document(
                page_content=content,
                metadata={"source": "培养方案/学业规章", "section": title.strip()},
            )
        )
    return docs


_retriever: BM25Retriever | None = None


def get_retriever() -> BM25Retriever:
    global _retriever
    if _retriever is None:
        _retriever = BM25Retriever(_load_regulations())
    return _retriever


def retrieve(query: str, k: int = 4) -> list[dict]:
    results = get_retriever().search(query, k=k)
    return [
        {
            "content": doc.page_content,
            "section": doc.metadata.get("section", ""),
            "source": doc.metadata.get("source", ""),
            "score": round(score, 3),
        }
        for doc, score in results
    ]
