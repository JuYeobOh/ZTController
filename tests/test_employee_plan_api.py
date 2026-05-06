"""Employee plan API 테스트."""
from datetime import date

import pytest

from app.models import DailyAssignment
from app.services.daily_plan import generate_daily_plan

WORK_DATE = date(2026, 4, 27)
DATE_STR = str(WORK_DATE)


def _generate(seeded_db):
    generate_daily_plan(WORK_DATE, seeded_db)
    return seeded_db


def test_no_plan_returns_404(client, seeded_db):
    """plan이 없으면 404를 반환한다."""
    resp = client.get(
        f"/api/v1/employees/enter-hr-staff/plans/{DATE_STR}?location_id=enterprise-hr",
    )
    assert resp.status_code == 404


def test_normal_employee_home_location_should_work_true(client, seeded_db):
    """카페 미배정 직원은 home_location에서 should_work_here=true를 받아야 한다."""
    _generate(seeded_db)

    # 카페 미배정 직원 찾기
    non_cafe = (
        seeded_db.query(DailyAssignment)
        .filter(
            DailyAssignment.work_date == WORK_DATE,
            DailyAssignment.is_cafe_dispatch == False,
        )
        .first()
    )
    assert non_cafe is not None

    resp = client.get(
        f"/api/v1/employees/{non_cafe.employee_id}/plans/{DATE_STR}"
        f"?location_id={non_cafe.home_location_id}",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["should_work_here"] is True
    assert data["assigned_location_id"] == non_cafe.home_location_id
    assert len(data["tasks"]) > 0
    assert data["clock_in_at"] is not None
    assert data["clock_out_at"] is not None


def test_normal_employee_wrong_location_should_work_false(client, seeded_db):
    """카페 미배정 직원이 home이 아닌 곳을 요청하면 should_work_here=false."""
    _generate(seeded_db)

    non_cafe = (
        seeded_db.query(DailyAssignment)
        .filter(
            DailyAssignment.work_date == WORK_DATE,
            DailyAssignment.is_cafe_dispatch == False,
        )
        .first()
    )
    # home이 아닌 다른 위치 요청
    other_location = "outdoor-cafe-1"
    assert non_cafe.home_location_id != other_location

    resp = client.get(
        f"/api/v1/employees/{non_cafe.employee_id}/plans/{DATE_STR}"
        f"?location_id={other_location}",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["should_work_here"] is False
    assert data["tasks"] == []
    assert data["clock_in_at"] is None


def test_cafe_employee_home_location_should_work_false(client, seeded_db):
    """카페 배정 직원은 원래 home_location에서 should_work_here=false를 받아야 한다."""
    _generate(seeded_db)

    cafe_assignment = (
        seeded_db.query(DailyAssignment)
        .filter(
            DailyAssignment.work_date == WORK_DATE,
            DailyAssignment.is_cafe_dispatch == True,
        )
        .first()
    )
    if cafe_assignment is None:
        pytest.skip("No cafe dispatch happened for this date/seed")

    resp = client.get(
        f"/api/v1/employees/{cafe_assignment.employee_id}/plans/{DATE_STR}"
        f"?location_id={cafe_assignment.home_location_id}",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["should_work_here"] is False
    assert data["assigned_location_id"] == cafe_assignment.work_location_id
    assert data["tasks"] == []


def test_cafe_employee_cafe_location_should_work_true(client, seeded_db):
    """카페 배정 직원은 배정된 카페 location에서 should_work_here=true를 받아야 한다."""
    _generate(seeded_db)

    cafe_assignment = (
        seeded_db.query(DailyAssignment)
        .filter(
            DailyAssignment.work_date == WORK_DATE,
            DailyAssignment.is_cafe_dispatch == True,
        )
        .first()
    )
    if cafe_assignment is None:
        pytest.skip("No cafe dispatch happened for this date/seed")

    resp = client.get(
        f"/api/v1/employees/{cafe_assignment.employee_id}/plans/{DATE_STR}"
        f"?location_id={cafe_assignment.work_location_id}",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["should_work_here"] is True
    assert len(data["tasks"]) > 0


def test_plan_tasks_have_correct_structure(client, seeded_db):
    """plan tasks의 구조가 올바른지 검증."""
    _generate(seeded_db)

    non_cafe = (
        seeded_db.query(DailyAssignment)
        .filter(
            DailyAssignment.work_date == WORK_DATE,
            DailyAssignment.is_cafe_dispatch == False,
        )
        .first()
    )

    resp = client.get(
        f"/api/v1/employees/{non_cafe.employee_id}/plans/{DATE_STR}"
        f"?location_id={non_cafe.home_location_id}",
    )
    data = resp.json()
    for task in data["tasks"]:
        assert "run_task_id" in task
        assert "task_id" in task
        assert "task_type" in task
        assert task["task_type"] in ("clock_in", "work", "clock_out")
        assert "scheduled_at" in task
        assert "status" in task
        assert task["status"] == "planned"
