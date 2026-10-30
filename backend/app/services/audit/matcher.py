from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

_TAG_RE = re.compile(r"[（(【\[].*?[）)】\]]")
_SPACE_RE = re.compile(r"[\s\-—_·,，.。:：;；/\\]+")
_ROMAN_RE = re.compile(r"[ⅠⅡⅢⅣⅤⅥ]")
_ROMAN_MAP = {"Ⅰ": "1", "Ⅱ": "2", "Ⅲ": "3", "Ⅳ": "4", "Ⅴ": "5", "Ⅵ": "6"}
_CN_NUM_RE = re.compile(r"[一二三四五六七八九十]")
_CN_NUM_MAP = {"一": "1", "二": "2", "三": "3", "四": "4", "五": "5", "六": "6", "七": "7", "八": "8", "九": "9", "十": "10"}


def normalize_name(name: str) -> str:
    """课程名规范化：保留括号内语义（上/下、Java、英文），去掉空格与标点，统一罗马数字。

    注意不能把括号内容整体删除，否则“高等数学（上）”与“（下）”会变成同一门课。
    """
    s = (name or "").strip().lower()
    s = s.translate(str.maketrans({"（": "(", "）": ")", "Ⅰ": "1", "Ⅱ": "2", "Ⅲ": "3", "Ⅳ": "4", "Ⅴ": "5", "Ⅵ": "6"}))
    s = re.sub(r"[\s\-—_·,，.。:：;；/\\()\[\]【】]+", "", s)
    s = re.sub(r"(?<=[\u4e00-\u9fff])(iii|ii|iv|i)(?=[\u4e00-\u9fff0-9]|$)", lambda m: {"i": "1", "ii": "2", "iii": "3", "iv": "4"}[m.group(1)], s)
    s = _CN_NUM_RE.sub(lambda m: _CN_NUM_MAP.get(m.group(0), ""), s)
    s = s.replace("上册", "上").replace("下册", "下")
    return s


def char_ngrams(text: str, n: int = 2) -> set[str]:
    if len(text) <= n:
        return {text} if text else set()
    return {text[i : i + n] for i in range(len(text) - n + 1)}


def semantic_similarity(a: str, b: str) -> float:
    """离线语义近似：字符 n-gram 余弦 + 序列相似度。可替换为 bge-m3 向量检索。"""
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return 0.0
    ga, gb = char_ngrams(na), char_ngrams(nb)
    inter = len(ga & gb)
    cosine = inter / ((len(ga) ** 0.5) * (len(gb) ** 0.5)) if ga and gb else 0.0
    seq = SequenceMatcher(None, na, nb).ratio()
    return round(0.6 * cosine + 0.4 * seq, 4)


@dataclass
class MatchCandidate:
    code: str
    name: str
    score: float
    method: str


@dataclass
class MatchResult:
    course_code: str | None
    course_name: str | None
    confidence: float
    method: str  # L1 / L2 / L3 / pending
    need_confirm: bool
    candidates: list[MatchCandidate] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "course_code": self.course_code,
            "course_name": self.course_name,
            "confidence": self.confidence,
            "method": self.method,
            "need_confirm": self.need_confirm,
            "candidates": [c.__dict__ for c in self.candidates],
        }


class CourseMatcher:
    """三级兜底：课程号精确 → 名称规范化/别名 → 语义近似 → 人工确认。"""

    def __init__(self, courses: list[dict], aliases: list[dict] | None = None):
        self.courses = {c["code"]: c for c in courses}
        self.by_norm = {normalize_name(c["name"]): c["code"] for c in courses}
        self.aliases = {normalize_name(a["alias"]): a["course_code"] for a in (aliases or [])}

    def match(self, raw_name: str, raw_code: str = "") -> MatchResult:
        raw_code = (raw_code or "").strip()
        if raw_code and raw_code in self.courses:
            c = self.courses[raw_code]
            return MatchResult(c["code"], c["name"], 1.0, "L1", False)

        norm = normalize_name(raw_name)
        if norm in self.aliases:
            code = self.aliases[norm]
            return MatchResult(code, self.courses[code]["name"], 0.99, "L2", False)
        if norm in self.by_norm:
            code = self.by_norm[norm]
            return MatchResult(code, self.courses[code]["name"], 0.98, "L2", False)

        scored: list[MatchCandidate] = []
        for code, c in self.courses.items():
            sim = semantic_similarity(raw_name, c["name"])
            if sim >= 0.55:
                scored.append(MatchCandidate(code, c["name"], sim, "L3"))
        scored.sort(key=lambda x: x.score, reverse=True)
        top = scored[:5]
        if top and top[0].score >= 0.85:
            return MatchResult(top[0].code, top[0].name, top[0].score, "L3", False, top)
        return MatchResult(None, None, top[0].score if top else 0.0, "pending", True, top)
