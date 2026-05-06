from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.config import settings
from app.models import DailyAssignment, Employee, RunTask
from app.services.task_loader import get_clock_in_task, get_clock_out_task, get_work_tasks
from app.utils.random_seed import get_seeded_random, make_daily_seed
from app.utils.time import to_utc_naive

_CAFE_LOCATIONS = ["outdoor-cafe-1", "outdoor-cafe-2"]
_CAFE_PROB = 0.3
_TASK_GAP_MIN = 30 * 60  # 작업 간 최소 간격: 30분 (초)
_TASK_GAP_MAX = 60 * 60  # 작업 간 최대 간격: 60분 (초)


def _plan_exists(work_date: date, db: Session) -> bool:
    return (
        db.query(DailyAssignment)
        .filter(DailyAssignment.work_date == work_date)
        .first()
    ) is not None


def _has_active_tasks(work_date: date, db: Session) -> bool:
    """running/succeeded/failed 상태의 task가 하나라도 있으면 True."""
    return (
        db.query(RunTask)
        .filter(
            RunTask.work_date == work_date,
            RunTask.status.in_(["running", "succeeded", "failed"]),
        )
        .first()
    ) is not None


def _delete_plan(work_date: date, db: Session) -> None:
    db.query(RunTask).filter(RunTask.work_date == work_date).delete()
    db.query(DailyAssignment).filter(DailyAssignment.work_date == work_date).delete()
    db.flush()


def _build_summary(work_date: date, cafe_assignments: dict[str, str], db: Session) -> dict:
    assignments = (
        db.query(DailyAssignment).filter(DailyAssignment.work_date == work_date).all()
    )
    run_tasks = db.query(RunTask).filter(RunTask.work_date == work_date).all()
    return {
        "work_date": str(work_date),
        "total_employees": len(assignments),
        "cafe_dispatches": len(cafe_assignments),
        "total_run_tasks": len(run_tasks),
        "cafe_assignments": cafe_assignments,
        "assignments": assignments,
        "run_tasks": run_tasks,
    }


def generate_daily_plan(
    work_date: date, db: Session, force: bool = False
) -> dict:
    """
    Returns a summary dict. Raises ValueError when the plan cannot be generated.
    """
    if _plan_exists(work_date, db):
        if not force:
            return _build_summary(work_date, _get_existing_cafe_assignments(work_date, db), db)
        if _has_active_tasks(work_date, db):
            raise ValueError(
                f"Cannot regenerate plan for {work_date}: "
                "some tasks are already running or completed."
            )
        _delete_plan(work_date, db)

    tz = ZoneInfo(settings.CONTROLLER_TIMEZONE)
    seed_str = make_daily_seed(str(work_date))
    rng = get_seeded_random(seed_str)

    # 직원 목록 (재현성을 위해 employee_id 순 정렬)
    employees: list[Employee] = (
        db.query(Employee)
        .filter(Employee.active == True)
        .order_by(Employee.employee_id)
        .all()
    )

    work_tasks = get_work_tasks(db)
    clock_in_def = get_clock_in_task(db)
    clock_out_def = get_clock_out_task(db)

    # ── Cafe dispatch ─────────────────────────────────────────────────────────
    eligible = sorted(
        [e for e in employees if e.eligible_for_cafe],
        key=lambda e: e.employee_id,
    )
    # employee_id -> cafe_location_id
    cafe_dispatch: dict[str, str] = {}

    for cafe_loc in _CAFE_LOCATIONS:
        if rng.random() < _CAFE_PROB:
            already = set(cafe_dispatch.keys())
            available = [e for e in eligible if e.employee_id not in already]
            if available:
                chosen = rng.choice(available)
                cafe_dispatch[chosen.employee_id] = cafe_loc

    # cafe_location_id -> employee_id (요약용)
    cafe_assignments: dict[str, str] = {v: k for k, v in cafe_dispatch.items()}

    # ── 직원별 assignment + run_tasks 생성 ────────────────────────────────────
    date_prefix = str(work_date).replace("-", "")

    work_tasks_sorted = sorted(work_tasks, key=lambda t: t.task_id)

    for employee in employees:
        if employee.employee_id in cafe_dispatch:
            work_location_id = cafe_dispatch[employee.employee_id]
            is_cafe = True
        else:
            work_location_id = employee.home_location_id
            is_cafe = False

        # clock_in: 08:00 ~ 10:00 KST  (0 ~ 7200 seconds offset)
        clock_in_kst = datetime(
            work_date.year, work_date.month, work_date.day, 8, 0, 0, tzinfo=tz
        ) + timedelta(seconds=rng.randint(0, 7200))

        # clock_out: 17:00 ~ 19:00 KST (0 ~ 7200 seconds offset)
        clock_out_kst = datetime(
            work_date.year, work_date.month, work_date.day, 17, 0, 0, tzinfo=tz
        ) + timedelta(seconds=rng.randint(0, 7200))

        clock_in_utc = to_utc_naive(clock_in_kst)
        clock_out_utc = to_utc_naive(clock_out_kst)

        db.add(
            DailyAssignment(
                work_date=work_date,
                employee_id=employee.employee_id,
                home_location_id=employee.home_location_id,
                work_location_id=work_location_id,
                is_cafe_dispatch=is_cafe,
                cafe_location_id=cafe_dispatch.get(employee.employee_id),
                clock_in_at=clock_in_utc,
                clock_out_at=clock_out_utc,
                random_seed=seed_str,
            )
        )

        seq = 1

        # clock_in task
        if clock_in_def:
            db.add(
                RunTask(
                    run_task_id=f"{date_prefix}-{employee.employee_id}-{seq:03d}",
                    work_date=work_date,
                    task_id=clock_in_def.task_id,
                    employee_id=employee.employee_id,
                    home_location_id=employee.home_location_id,
                    work_location_id=work_location_id,
                    task_type="clock_in",
                    site=clock_in_def.site,
                    module=clock_in_def.module,
                    action=clock_in_def.action,
                    params_json=clock_in_def.params_json,
                    scheduled_at=clock_in_utc,
                    status="planned",
                )
            )
            seq += 1

        # work tasks: clock_in ~ clock_out 사이를 30~60분 간격으로 채움
        if work_tasks_sorted:
            work_secs = (clock_out_kst - clock_in_kst).total_seconds()
            current = float(rng.randint(_TASK_GAP_MIN, _TASK_GAP_MAX))
            selected = []
            offsets = []
            while current < work_secs:
                offsets.append(current)
                selected.append(rng.choice(work_tasks_sorted))
                current += rng.randint(_TASK_GAP_MIN, _TASK_GAP_MAX)

            for task_def, offset in zip(selected, offsets):
                scheduled_utc = to_utc_naive(clock_in_kst + timedelta(seconds=offset))
                db.add(
                    RunTask(
                        run_task_id=f"{date_prefix}-{employee.employee_id}-{seq:03d}",
                        work_date=work_date,
                        task_id=task_def.task_id,
                        employee_id=employee.employee_id,
                        home_location_id=employee.home_location_id,
                        work_location_id=work_location_id,
                        task_type="work",
                        site=task_def.site,
                        module=task_def.module,
                        action=task_def.action,
                        params_json=task_def.params_json,
                        scheduled_at=scheduled_utc,
                        status="planned",
                    )
                )
                seq += 1

        # clock_out task
        if clock_out_def:
            db.add(
                RunTask(
                    run_task_id=f"{date_prefix}-{employee.employee_id}-{seq:03d}",
                    work_date=work_date,
                    task_id=clock_out_def.task_id,
                    employee_id=employee.employee_id,
                    home_location_id=employee.home_location_id,
                    work_location_id=work_location_id,
                    task_type="clock_out",
                    site=clock_out_def.site,
                    module=clock_out_def.module,
                    action=clock_out_def.action,
                    params_json=clock_out_def.params_json,
                    scheduled_at=clock_out_utc,
                    status="planned",
                )
            )

    db.commit()
    return _build_summary(work_date, cafe_assignments, db)


def _get_existing_cafe_assignments(work_date: date, db: Session) -> dict[str, str]:
    rows = (
        db.query(DailyAssignment)
        .filter(
            DailyAssignment.work_date == work_date,
            DailyAssignment.is_cafe_dispatch == True,
        )
        .all()
    )
    return {row.work_location_id: row.employee_id for row in rows}
