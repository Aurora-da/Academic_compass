from __future__ import annotations

import pytest

from app.services.plan.terms import (
    academic_to_index,
    academic_year_of,
    completed_academic_years,
    graduation_term,
    index_to_academic,
    index_to_term,
    remaining_terms,
    term_index,
    term_label,
)


@pytest.mark.parametrize(
    "term,index", [("1-1", 0), ("1-2", 1), ("2-1", 2), ("2-2", 3), ("3-1", 4), ("3-2", 5), ("4-1", 6), ("4-2", 7)]
)
def test_term_index(term, index):
    assert term_index(term) == index


@pytest.mark.parametrize("term", ["", "1", "1-3", "0-1", "7-1", "a-b"])
def test_invalid_term(term):
    with pytest.raises(ValueError):
        term_index(term)


def test_term_label():
    assert term_label("3-2") == "3-2（大三春）"


@pytest.mark.parametrize(
    "academic,entry,index",
    [
        ("2023-2024-1", 2023, 0),
        ("2023-2024-2", 2023, 1),
        ("2024-2025-1", 2023, 2),
        ("2025-2026-2", 2023, 5),
        ("2025-2026-2", 2024, 3),
    ],
)
def test_academic_index(academic, entry, index):
    assert academic_to_index(academic, entry) == index


def test_academic_roundtrip():
    for idx in range(8):
        academic = index_to_academic(idx, 2023)
        assert academic_to_index(academic, 2023) == idx
        assert index_to_term(idx) == ["1-1", "1-2", "2-1", "2-2", "3-1", "3-2", "4-1", "4-2"][idx]


def test_completed_academic_years():
    assert completed_academic_years(2023, "2025-2026-2") == ["2023-2024", "2024-2025"]


def test_academic_year_of():
    assert academic_year_of("2025-2026-2") == "2025-2026"


def test_remaining_terms_standard():
    terms = remaining_terms("2025-2026-2", "2026-2027-2", 2023)
    assert terms == [5, 6, 7]
    assert remaining_terms("2025-2026-2", "2026-2027-2", 2023, include_current=False) == [6, 7]


def test_remaining_terms_three_year():
    assert remaining_terms("2025-2026-2", graduation_term(2023, 3), 2023) == [5]


def test_graduation_term():
    assert graduation_term(2023, 3) == "2025-2026-2"
    assert graduation_term(2023, 4) == "2026-2027-2"
    assert graduation_term(2023, 5) == "2027-2028-2"
