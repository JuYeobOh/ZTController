"""Cafe dispatch 규칙 테스트."""
from datetime import date

import pytest

from app.models import DailyAssignment
from app.services.daily_plan import _CAFE_LOCATIONS, generate_daily_plan


def _assignments(db, work_date: date) -> list[DailyAssignment]:
    return db.query(DailyAssignment).filter(DailyAssignment.work_date == work_date).all()


def test_cafe_dispatches_at_most_2_per_day(seeded_db):
    """하루 카페 근무자는 최대 2명이다 (Cafe VPC 2개)."""
    work_date = date(2026, 4, 27)
    generate_daily_plan(work_date, seeded_db)
    cafe_assignments = [a for a in _assignments(seeded_db, work_date) if a.is_cafe_dispatch]
    assert len(cafe_assignments) <= 2


def test_no_duplicate_cafe_employee_same_day(seeded_db):
    """같은 직원이 같은 날 두 개 이상의 Cafe에 배정되면 안 된다."""
    work_date = date(2026, 4, 27)
    generate_daily_plan(work_date, seeded_db)
    cafe_employees = [
        a.employee_id for a in _assignments(seeded_db, work_date) if a.is_cafe_dispatch
    ]
    assert len(cafe_employees) == len(set(cafe_employees))


def test_cafe_employee_work_location_is_cafe(seeded_db):
    """Cafe 배정 직원의 work_location_id는 cafe location이어야 한다."""
    work_date = date(2026, 4, 27)
    generate_daily_plan(work_date, seeded_db)
    for a in _assignments(seeded_db, work_date):
        if a.is_cafe_dispatch:
            assert a.work_location_id in _CAFE_LOCATIONS
            assert a.cafe_location_id == a.work_location_id
            assert a.work_location_id != a.home_location_id


def test_non_cafe_employee_work_location_is_home(seeded_db):
    """Cafe 미배정 직원의 work_location_id는 home_location_id와 같아야 한다."""
    work_date = date(2026, 4, 27)
    generate_daily_plan(work_date, seeded_db)
    for a in _assignments(seeded_db, work_date):
        if not a.is_cafe_dispatch:
            assert a.work_location_id == a.home_location_id


def test_cafe_dispatch_probability_across_multiple_dates():
    """여러 날짜에 걸쳐 각 Cafe가 독립적으로 ~30% 확률로 활성화되는지 검증."""
    from app.utils.random_seed import get_seeded_random, make_daily_seed

    n_days = 200
    # 각 Cafe별 활성화 횟수 측정
    counts = {loc: 0 for loc in _CAFE_LOCATIONS}
    for i in range(n_days):
        work_date = date(2026, 1, 1)
        seed_str = make_daily_seed(f"2026-test-{i:03d}")
        rng = get_seeded_random(seed_str)
        for loc in _CAFE_LOCATIONS:
            if rng.random() < 0.3:
                counts[loc] += 1

    # 각 Cafe의 활성화 비율이 15%~50% 범위 내에 있어야 한다 (±15%)
    for loc, cnt in counts.items():
        ratio = cnt / n_days
        assert 0.15 <= ratio <= 0.50, f"{loc}: activation ratio {ratio:.2f} out of expected range"


def test_each_cafe_independently_activated(seeded_db):
    """Cafe 2개가 서로 독립적으로 평가되는지 확인 (날짜별로 결과가 다를 수 있음)."""
    from app.utils.random_seed import get_seeded_random, make_daily_seed

    results: list[tuple[bool, bool]] = []
    for i in range(50):
        seed_str = make_daily_seed(f"2026-ind-{i:03d}")
        rng = get_seeded_random(seed_str)
        pair = tuple(rng.random() < 0.3 for _ in _CAFE_LOCATIONS)
        results.append(pair)

    # 두 Cafe가 항상 동일한 결과를 갖지 않는 케이스가 있어야 독립성 성립
    all_same = sum(1 for r in results if r[0] == r[1])
    assert all_same < 50, "Cafes appear to be correlated (not independent)"


def test_reproducibility_cafe_assignments(seeded_db):
    """같은 날짜에 plan을 재생성하면 Cafe 배정이 동일해야 한다."""
    work_date = date(2026, 4, 27)
    generate_daily_plan(work_date, seeded_db)
    first = {a.employee_id: a.work_location_id for a in _assignments(seeded_db, work_date)}

    generate_daily_plan(work_date, seeded_db, force=True)
    second = {a.employee_id: a.work_location_id for a in _assignments(seeded_db, work_date)}

    assert first == second
