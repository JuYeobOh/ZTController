from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import ResultMetadata, RunTask, TaskEvent
from app.utils.time import utc_now

_TERMINAL = {"succeeded", "failed", "skipped", "cancelled"}
_VALID_STATUSES = {"running", "succeeded", "failed", "skipped", "cancelled"}


def _get_task_or_404(run_task_id: str, db: Session) -> RunTask:
    rt = db.query(RunTask).filter(RunTask.run_task_id == run_task_id).first()
    if rt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run_task not found")
    return rt


def _verify_ownership(rt: RunTask, employee_id: str, location_id: str) -> None:
    if rt.employee_id != employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"employee_id mismatch: expected {rt.employee_id}",
        )
    if rt.work_location_id != location_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"location_id mismatch: expected {rt.work_location_id}",
        )


def update_task_status(
    run_task_id: str,
    employee_id: str,
    location_id: str,
    new_status: str,
    result_path: str | None,
    error_message: str | None,
    db: Session,
) -> RunTask:
    if new_status not in _VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status: {new_status}",
        )

    rt = _get_task_or_404(run_task_id, db)
    _verify_ownership(rt, employee_id, location_id)

    rt.status = new_status
    now = utc_now()

    if new_status == "running":
        rt.started_at = now
    if new_status in _TERMINAL:
        rt.completed_at = now
    if result_path is not None:
        rt.result_path = result_path
    if error_message is not None:
        rt.error_message = error_message

    rt.updated_at = now

    db.add(
        TaskEvent(
            run_task_id=run_task_id,
            employee_id=employee_id,
            location_id=location_id,
            event_type=f"status_changed_to_{new_status}",
            message=error_message,
            payload_json={"result_path": result_path},
        )
    )
    db.commit()
    db.refresh(rt)
    return rt


def add_task_event(
    run_task_id: str,
    employee_id: str,
    location_id: str,
    event_type: str,
    message: str | None,
    payload: dict | None,
    db: Session,
) -> TaskEvent:
    rt = _get_task_or_404(run_task_id, db)
    _verify_ownership(rt, employee_id, location_id)

    ev = TaskEvent(
        run_task_id=run_task_id,
        employee_id=employee_id,
        location_id=location_id,
        event_type=event_type,
        message=message,
        payload_json=payload,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


def add_result_metadata(
    run_task_id: str,
    employee_id: str,
    location_id: str,
    result_root_path: str,
    screenshots_path: str | None,
    browser_trace_path: str | None,
    network_log_path: str | None,
    metadata: dict | None,
    db: Session,
) -> ResultMetadata:
    rt = _get_task_or_404(run_task_id, db)
    _verify_ownership(rt, employee_id, location_id)

    rm = ResultMetadata(
        run_task_id=run_task_id,
        employee_id=employee_id,
        location_id=location_id,
        result_root_path=result_root_path,
        screenshots_path=screenshots_path,
        browser_trace_path=browser_trace_path,
        network_log_path=network_log_path,
        metadata_json=metadata,
    )
    db.add(rm)
    db.commit()
    db.refresh(rm)
    return rm
