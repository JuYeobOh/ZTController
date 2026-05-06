"""Daily plan 생성 기본 테스트."""
from datetime import date, timezone
from zoneinfo import ZoneInfo

import pytest

from app.models import DailyAssignment, RunTask
from app.services.daily_plan import generate_daily_plan

KST = ZoneInfo("Asia/Seoul")
WORK_DATE = date(2026, 4, 27)


def _get_assignments(db) -> list[DailyAssignment]:
    return db.query(DailyAssignment).filter(DailyAssignment.work_date == WORK_DATE).all()


def _kst(dt):
    """UTC naive datetime → KST-aware datetime."""
    return dt.replace(tzinfo=timezone.utc).astimezone(KST)


def test_daily_plan_reproducibility(seeded_db):
    """같은 날짜 + 같은 seed → 동일한 결과 재생성."""
    generate_daily_plan(WORK_DATE, seeded_db, force=False)

    assignments_1 = {
        a.employee_id: (a.work_location_id, str(a.clock_in_at), str(a.clock_out_at))
        for a in _get_assignments(seeded_db)
    }

    generate_daily_plan(WORK_DATE, seeded_db, force=True)

    assignments_2 = {
        a.employee_id: (a.work_location_id, str(a.clock_in_at), str(a.clock_out_at))
        for a in _get_assignments(seeded_db)
    }

    assert assignments_1 == assignments_2


def test_all_active_employees_have_assignment(seeded_db):
    """모든 active 직원이 assignment를 가져야 한다."""
    from app.models import Employee

    generate_daily_plan(WORK_DATE, seeded_db)
    employees = seeded_db.query(Employee).filter(Employee.active == True).all()
    assigned_ids = {a.employee_id for a in _get_assignments(seeded_db)}
    for emp in employees:
        assert emp.employee_id in assigned_ids


def test_clock_in_time_range(seeded_db):
    """출근 시간은 08:00~10:00 KST 사이여야 한다."""
    generate_daily_plan(WORK_DATE, seeded_db)
    for assignment in _get_assignments(seeded_db):
        ci = _kst(assignment.clock_in_at)
        assert ci.hour >= 8, f"{assignment.employee_id} clock_in hour {ci.hour} < 8"
        assert ci.hour <= 10, f"{assignment.employee_id} clock_in hour {ci.hour} > 10"
        if ci.hour == 10:
            assert ci.minute == 0 and ci.second == 0


def test_clock_out_time_range(seeded_db):
    """퇴근 시간은 17:00~19:00 KST 사이여야 한다."""
    generate_daily_plan(WORK_DATE, seeded_db)
    for assignment in _get_assignments(seeded_db):
        co = _kst(assignment.clock_out_at)
        assert co.hour >= 17, f"{assignment.employee_id} clock_out hour {co.hour} < 17"
        assert co.hour <= 19, f"{assignment.employee_id} clock_out hour {co.hour} > 19"
        if co.hour == 19:
            assert co.minute == 0 and co.second == 0


def test_clock_in_before_clock_out(seeded_db):
    """출근 시간은 퇴근 시간보다 앞서야 한다."""
    generate_daily_plan(WORK_DATE, seeded_db)
    for a in _get_assignments(seeded_db):
        assert a.clock_in_at < a.clock_out_at


def test_work_tasks_between_clock_in_and_out(seeded_db):
    """work 타입 task의 scheduled_at은 clock_in/clock_out 사이여야 한다."""
    generate_daily_plan(WORK_DATE, seeded_db)
    assignments = {a.employee_id: a for a in _get_assignments(seeded_db)}
    run_tasks = (
        seeded_db.query(RunTask)
        .filter(RunTask.work_date == WORK_DATE, RunTask.task_type == "work")
        .all()
    )
    for rt in run_tasks:
        a = assignments[rt.employee_id]
        assert rt.scheduled_at > a.clock_in_at, (
            f"{rt.run_task_id} scheduled_at not after clock_in"
        )
        assert rt.scheduled_at < a.clock_out_at, (
            f"{rt.run_task_id} scheduled_at not before clock_out"
        )


def test_each_employee_has_clock_in_and_out_tasks(seeded_db):
    """각 직원은 clock_in task와 clock_out task를 정확히 1개씩 가져야 한다."""
    generate_daily_plan(WORK_DATE, seeded_db)
    from app.models import Employee

    employees = seeded_db.query(Employee).filter(Employee.active == True).all()
    for emp in employees:
        tasks = (
            seeded_db.query(RunTask)
            .filter(RunTask.work_date == WORK_DATE, RunTask.employee_id == emp.employee_id)
            .all()
        )
        types = [t.task_type for t in tasks]
        assert types.count("clock_in") == 1
        assert types.count("clock_out") == 1


def test_force_false_does_not_regenerate(seeded_db):
    """force=False이고 plan이 있으면 재생성하지 않는다."""
    generate_daily_plan(WORK_DATE, seeded_db)
    first_ids = {
        rt.run_task_id
        for rt in seeded_db.query(RunTask).filter(RunTask.work_date == WORK_DATE).all()
    }
    generate_daily_plan(WORK_DATE, seeded_db, force=False)
    second_ids = {
        rt.run_task_id
        for rt in seeded_db.query(RunTask).filter(RunTask.work_date == WORK_DATE).all()
    }
    assert first_ids == second_ids


def test_force_true_with_active_tasks_raises(seeded_db):
    """force=True이지만 실행 중인 task가 있으면 ValueError."""
    generate_daily_plan(WORK_DATE, seeded_db)
    # 첫 번째 task를 running으로 변경
    rt = seeded_db.query(RunTask).filter(RunTask.work_date == WORK_DATE).first()
    rt.status = "running"
    seeded_db.commit()

    with pytest.raises(ValueError, match="running or completed"):
        generate_daily_plan(WORK_DATE, seeded_db, force=True)
