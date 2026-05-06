from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import DailyAssignment, RunTask
from app.schemas import (
    AssignmentItem,
    DailyPlanResponse,
    GenerateDailyPlanRequest,
    RunTaskItem,
    RunTaskListResponse,
    SeedReloadResponse,
)
from app.services.daily_plan import generate_daily_plan
from app.services.seed_loader import reload_seed
from app.utils.time import format_kst

router = APIRouter(prefix="/admin")


# ── Daily plan generation ─────────────────────────────────────────────────────

@router.post("/daily-plans/generate", response_model=DailyPlanResponse)
def api_generate_daily_plan(
    body: GenerateDailyPlanRequest,
    db: Session = Depends(get_db),
):
    try:
        work_date = date.fromisoformat(body.work_date)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid work_date: {body.work_date}",
        )

    try:
        summary = generate_daily_plan(work_date, db, force=body.force)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    return _summary_to_response(summary)


# ── Daily plan detail ─────────────────────────────────────────────────────────

@router.get("/daily-plans/{work_date}", response_model=DailyPlanResponse)
def api_get_daily_plan(
    work_date: date,
    db: Session = Depends(get_db),
):
    assignments = (
        db.query(DailyAssignment)
        .filter(DailyAssignment.work_date == work_date)
        .all()
    )
    if not assignments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No daily plan for {work_date}",
        )
    run_tasks = db.query(RunTask).filter(RunTask.work_date == work_date).all()
    cafe_assignments = {
        a.work_location_id: a.employee_id for a in assignments if a.is_cafe_dispatch
    }
    return DailyPlanResponse(
        work_date=str(work_date),
        total_employees=len(assignments),
        cafe_dispatches=len(cafe_assignments),
        total_run_tasks=len(run_tasks),
        cafe_assignments=cafe_assignments,
        assignments=[_assignment_item(a) for a in assignments],
        run_tasks=[_run_task_item(rt) for rt in run_tasks],
    )


# ── Run task list ─────────────────────────────────────────────────────────────

@router.get("/run-tasks", response_model=RunTaskListResponse)
def api_list_run_tasks(
    work_date: Optional[date] = Query(None),
    employee_id: Optional[str] = Query(None),
    task_status: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    q = db.query(RunTask)
    if work_date:
        q = q.filter(RunTask.work_date == work_date)
    if employee_id:
        q = q.filter(RunTask.employee_id == employee_id)
    if task_status:
        q = q.filter(RunTask.status == task_status)
    items = q.order_by(RunTask.scheduled_at).all()
    return RunTaskListResponse(total=len(items), items=[_run_task_item(rt) for rt in items])


# ── Seed reload ───────────────────────────────────────────────────────────────

@router.post("/seed/reload", response_model=SeedReloadResponse)
def api_seed_reload(
    db: Session = Depends(get_db),
):
    try:
        counts = reload_seed(
            db,
            settings.EMPLOYEE_SEED_FILE,
            settings.LOCATION_SEED_FILE,
            settings.TASK_SEED_FILE,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return SeedReloadResponse(**counts)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _summary_to_response(summary: dict) -> DailyPlanResponse:
    return DailyPlanResponse(
        work_date=summary["work_date"],
        total_employees=summary["total_employees"],
        cafe_dispatches=summary["cafe_dispatches"],
        total_run_tasks=summary["total_run_tasks"],
        cafe_assignments=summary["cafe_assignments"],
        assignments=[_assignment_item(a) for a in summary["assignments"]],
        run_tasks=[_run_task_item(rt) for rt in summary["run_tasks"]],
    )


def _assignment_item(a: DailyAssignment) -> AssignmentItem:
    return AssignmentItem(
        employee_id=a.employee_id,
        home_location_id=a.home_location_id,
        work_location_id=a.work_location_id,
        is_cafe_dispatch=a.is_cafe_dispatch,
        cafe_location_id=a.cafe_location_id,
        clock_in_at=format_kst(a.clock_in_at),
        clock_out_at=format_kst(a.clock_out_at),
    )


def _run_task_item(rt: RunTask) -> RunTaskItem:
    return RunTaskItem(
        run_task_id=rt.run_task_id,
        employee_id=rt.employee_id,
        task_id=rt.task_id,
        task_type=rt.task_type,
        site=rt.site,
        module=rt.module,
        action=rt.action,
        scheduled_at=format_kst(rt.scheduled_at),
        status=rt.status,
    )
