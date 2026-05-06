from typing import Any, Optional

from pydantic import BaseModel


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    time: str


# ── Employee Plan ─────────────────────────────────────────────────────────────

class TaskItem(BaseModel):
    run_task_id: str
    task_id: str
    task_type: str
    site: Optional[str] = None
    module: Optional[str] = None
    action: str
    scheduled_at: str
    status: str


class EmployeePlanResponse(BaseModel):
    work_date: str
    employee_id: str
    requested_location_id: str
    assigned_location_id: str
    should_work_here: bool
    clock_in_at: Optional[str] = None
    clock_out_at: Optional[str] = None
    tasks: list[TaskItem] = []


# ── Task Status Update ────────────────────────────────────────────────────────

class TaskStatusUpdateRequest(BaseModel):
    employee_id: str
    location_id: str
    status: str
    result_path: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class TaskStatusUpdateResponse(BaseModel):
    run_task_id: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


# ── Task Event ────────────────────────────────────────────────────────────────

class TaskEventRequest(BaseModel):
    employee_id: str
    location_id: str
    event_type: str
    message: Optional[str] = None
    payload: Optional[dict[str, Any]] = None


class TaskEventResponse(BaseModel):
    id: int
    run_task_id: str
    event_type: str
    created_at: str


# ── Result Metadata ───────────────────────────────────────────────────────────

class ResultMetadataRequest(BaseModel):
    employee_id: str
    location_id: str
    result_root_path: str
    screenshots_path: Optional[str] = None
    browser_trace_path: Optional[str] = None
    network_log_path: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class ResultMetadataResponse(BaseModel):
    id: int
    run_task_id: str
    result_root_path: str


# ── Admin: Daily Plan ─────────────────────────────────────────────────────────

class GenerateDailyPlanRequest(BaseModel):
    work_date: str
    force: bool = False


class AssignmentItem(BaseModel):
    employee_id: str
    home_location_id: str
    work_location_id: str
    is_cafe_dispatch: bool
    cafe_location_id: Optional[str] = None
    clock_in_at: str
    clock_out_at: str


class RunTaskItem(BaseModel):
    run_task_id: str
    employee_id: str
    task_id: str
    task_type: str
    site: Optional[str] = None
    module: Optional[str] = None
    action: str
    scheduled_at: str
    status: str


class DailyPlanResponse(BaseModel):
    work_date: str
    total_employees: int
    cafe_dispatches: int
    total_run_tasks: int
    cafe_assignments: dict[str, str]  # cafe_location_id -> employee_id
    assignments: list[AssignmentItem] = []
    run_tasks: list[RunTaskItem] = []


# ── Admin: Run Task List ──────────────────────────────────────────────────────

class RunTaskListResponse(BaseModel):
    total: int
    items: list[RunTaskItem]


# ── Admin: Seed Reload ────────────────────────────────────────────────────────

class SeedReloadResponse(BaseModel):
    employees_loaded: int
    locations_loaded: int
    tasks_loaded: int
