from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DailyAssignment, RunTask
from app.schemas import EmployeePlanResponse, TaskItem
from app.utils.time import format_kst

router = APIRouter()


def _build_plan_response(
    work_date: date,
    employee_id: str,
    requested_location_id: str,
    assignment: DailyAssignment,
    db: Session,
) -> EmployeePlanResponse:
    assigned = assignment.work_location_id
    should_work = assigned == requested_location_id

    tasks: list[TaskItem] = []
    if should_work:
        run_tasks = (
            db.query(RunTask)
            .filter(
                RunTask.work_date == work_date,
                RunTask.employee_id == employee_id,
            )
            .order_by(RunTask.scheduled_at)
            .all()
        )
        tasks = [
            TaskItem(
                run_task_id=rt.run_task_id,
                task_id=rt.task_id,
                task_type=rt.task_type,
                site=rt.site,
                module=rt.module,
                action=rt.action,
                scheduled_at=format_kst(rt.scheduled_at),
                status=rt.status,
            )
            for rt in run_tasks
        ]

    return EmployeePlanResponse(
        work_date=str(work_date),
        employee_id=employee_id,
        requested_location_id=requested_location_id,
        assigned_location_id=assigned,
        should_work_here=should_work,
        clock_in_at=format_kst(assignment.clock_in_at) if should_work else None,
        clock_out_at=format_kst(assignment.clock_out_at) if should_work else None,
        tasks=tasks,
    )


@router.get(
    "/employees/{employee_id}/plans/today",
    response_model=EmployeePlanResponse,
)
def get_today_plan(
    employee_id: str,
    location_id: str = Query(...),
    db: Session = Depends(get_db),
):
    today = date.today()
    assignment = (
        db.query(DailyAssignment)
        .filter(
            DailyAssignment.work_date == today,
            DailyAssignment.employee_id == employee_id,
        )
        .first()
    )
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No daily plan generated for {today}",
        )
    return _build_plan_response(today, employee_id, location_id, assignment, db)


@router.get(
    "/employees/{employee_id}/plans/{work_date}",
    response_model=EmployeePlanResponse,
)
def get_plan_by_date(
    employee_id: str,
    work_date: date,
    location_id: str = Query(...),
    db: Session = Depends(get_db),
):
    assignment = (
        db.query(DailyAssignment)
        .filter(
            DailyAssignment.work_date == work_date,
            DailyAssignment.employee_id == employee_id,
        )
        .first()
    )
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No daily plan for employee {employee_id} on {work_date}",
        )
    return _build_plan_response(work_date, employee_id, location_id, assignment, db)
