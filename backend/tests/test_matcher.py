from __future__ import annotations

import pytest

from app.services.audit.matcher import (
    CourseMatcher,
    normalize_name,
    semantic_similarity,
)


@pytest.fixture(scope="module")
def matcher(plan):
    return CourseMatcher([{"code": c.code, "name": c.name} for c in plan.course_map().values()])


def test_normalize_removes_brackets_and_spaces():
    assert normalize_name("高等数学 I（上）") == normalize_name("高等数学I(上)")


def test_normalize_roman_numerals():
    assert normalize_name("线性代数 I") == "线性代数1"
    assert normalize_name("大学物理（3）") == "大学物理3"


def test_normalize_removes_dashes_and_punctuation():
    assert normalize_name("面向对象程序设计(Java)") == "面向对象程序设计java"


def test_l1_code_match(matcher):
    result = matcher.match("随便写", "B034913")
    assert result.course_code == "B034913"
    assert result.method == "L1"
    assert result.confidence == 1.0
    assert not result.need_confirm


def test_l2_exact_name_match(matcher):
    result = matcher.match("数据结构", "")
    assert result.course_code == "B033905"
    assert result.method == "L2"
    assert result.confidence >= 0.98


def test_l2_variant_name_match(matcher):
    result = matcher.match("高等数学I(上)", "")
    assert result.course_code == "B113101"
    assert result.method == "L2"


def test_l2_alias_match(plan):
    matcher = CourseMatcher(
        [{"code": c.code, "name": c.name} for c in plan.course_map().values()],
        [{"alias": "高数A(上)", "course_code": "B113101"}],
    )
    result = matcher.match("高数A(上)", "")
    assert result.course_code == "B113101"
    assert result.method == "L2"


def test_l3_semantic_match(matcher):
    result = matcher.match("大数据技术", "")
    assert result.method in {"L3", "pending"}
    assert result.candidates


def test_pending_low_confidence(matcher):
    result = matcher.match("完全不存在的课程XYZ", "")
    assert result.need_confirm is True
    assert result.course_code is None


def test_similarity_order():
    high = semantic_similarity("数据结构", "数据结构")
    low = semantic_similarity("数据结构", "大学体育")
    assert high == 1.0
    assert low < high
