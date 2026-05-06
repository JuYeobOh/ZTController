from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    ResultMetadataRequest,
    ResultMetadataResponse,
    TaskEventRequest,
    TaskEventResponse,
    TaskStatusUpdateRequest,
    TaskStatusUpdateResponse,
)
from app.services.task_status import add_result_metadata, add_task_event, update_task_status
from app.utils.time import format_kst

router = APIRouter()


@router.post(
    "/run-tasks/{run_task_id}/status",
    response_model=TaskStatusUpdateResponse,
)
def update_status(
    run_task_id: str,
    body: TaskStatusUpdateRequest,
    db: Session = Depends(get_db),
):
    rt = update_task_status(
        run_task_id=run_task_id,
        employee_id=body.employee_id,
        location_id=body.location_id,
        new_status=body.status,
        result_path=body.result_path,
        error_message=body.error_message,
        db=db,
    )
    return TaskStatusUpdateResponse(
        run_task_id=rt.run_task_id,
        status=rt.status,
        started_at=format_kst(rt.started_at) if rt.started_at else None,
        completed_at=format_kst(rt.completed_at) if rt.completed_at else None,
    )


@router.post(
    "/run-tasks/{run_task_id}/events",
    response_model=TaskEventResponse,
)
def post_event(
    run_task_id: str,
    body: TaskEventRequest,
    db: Session = Depends(get_db),
):
    ev = add_task_event(
        run_task_id=run_task_id,
        employee_id=body.employee_id,
        location_id=body.location_id,
        event_type=body.event_type,
        message=body.message,
        payload=body.payload,
        db=db,
    )
    return TaskEventResponse(
        id=ev.id,
        run_task_id=ev.run_task_id,
        event_type=ev.event_type,
        created_at=format_kst(ev.created_at),
    )


@router.post(
    "/run-tasks/{run_task_id}/result",
    response_model=ResultMetadataResponse,
)
def post_result(
    run_task_id: str,
    body: ResultMetadataRequest,
    db: Session = Depends(get_db),
):
    rm = add_result_metadata(
        run_task_id=run_task_id,
        employee_id=body.employee_id,
        location_id=body.location_id,
        result_root_path=body.result_root_path,
        screenshots_path=body.screenshots_path,
        browser_trace_path=body.browser_trace_path,
        network_log_path=body.network_log_path,
        metadata=body.metadata,
        db=db,
    )
    return ResultMetadataResponse(
        id=rm.id,
        run_task_id=rm.run_task_id,
        result_root_path=rm.result_root_path,
    )
