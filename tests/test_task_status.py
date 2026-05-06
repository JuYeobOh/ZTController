"""Task 상태 업데이트 테스트."""
from datetime import date

import pytest

from app.models import DailyAssignment, RunTask
from app.services.daily_plan import generate_daily_plan

WORK_DATE = date(2026, 4, 27)
DATE_STR = str(WORK_DATE)


def _first_planned_task(seeded_db) -> RunTask:
    generate_daily_plan(WORK_DATE, seeded_db)
    return (
        seeded_db.query(RunTask)
        .filter(RunTask.work_date == WORK_DATE, RunTask.status == "planned")
        .first()
    )


def test_status_update_running_sets_started_at(client, seeded_db):
    """status=running 업데이트 시 started_at이 설정되어야 한다."""
    rt = _first_planned_task(seeded_db)
    resp = client.post(
        f"/api/v1/run-tasks/{rt.run_task_id}/status",
        json={
            "employee_id": rt.employee_id,
            "location_id": rt.work_location_id,
            "status": "running",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "running"
    assert data["started_at"] is not None
    assert data["completed_at"] is None


def test_status_update_succeeded_sets_completed_at(client, seeded_db):
    """status=succeeded 업데이트 시 completed_at이 설정되어야 한다."""
    rt = _first_planned_task(seeded_db)
    resp = client.post(
        f"/api/v1/run-tasks/{rt.run_task_id}/status",
        json={
            "employee_id": rt.employee_id,
            "location_id": rt.work_location_id,
            "status": "succeeded",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "succeeded"
    assert data["completed_at"] is not None


def test_status_update_wrong_employee_rejected(client, seeded_db):
    """employee_id가 일치하지 않으면 403을 반환해야 한다."""
    rt = _first_planned_task(seeded_db)
    resp = client.post(
        f"/api/v1/run-tasks/{rt.run_task_id}/status",
        json={
            "employee_id": "wrong-employee",
            "location_id": rt.work_location_id,
            "status": "running",
        },
    )
    assert resp.status_code == 403


def test_status_update_wrong_location_rejected(client, seeded_db):
    """location_id가 일치하지 않으면 403을 반환해야 한다."""
    rt = _first_planned_task(seeded_db)
    resp = client.post(
        f"/api/v1/run-tasks/{rt.run_task_id}/status",
        json={
            "employee_id": rt.employee_id,
            "location_id": "wrong-location",
            "status": "running",
        },
    )
    assert resp.status_code == 403


def test_status_update_invalid_status_rejected(client, seeded_db):
    """유효하지 않은 status 값은 422를 반환해야 한다."""
    rt = _first_planned_task(seeded_db)
    resp = client.post(
        f"/api/v1/run-tasks/{rt.run_task_id}/status",
        json={
            "employee_id": rt.employee_id,
            "location_id": rt.work_location_id,
            "status": "invalid-status",
        },
    )
    assert resp.status_code == 422


def test_status_update_nonexistent_task(client, seeded_db):
    """존재하지 않는 run_task_id는 404를 반환해야 한다."""
    generate_daily_plan(WORK_DATE, seeded_db)
    resp = client.post(
        "/api/v1/run-tasks/nonexistent-task-id/status",
        json={
            "employee_id": "enter-hr-staff",
            "location_id": "enterprise-hr",
            "status": "running",
        },
    )
    assert resp.status_code == 404


def test_event_upload(client, seeded_db):
    """task event 업로드가 성공해야 한다."""
    rt = _first_planned_task(seeded_db)
    resp = client.post(
        f"/api/v1/run-tasks/{rt.run_task_id}/events",
        json={
            "employee_id": rt.employee_id,
            "location_id": rt.work_location_id,
            "event_type": "browser_login_success",
            "message": "Login succeeded",
            "payload": {"url": "https://groupoffice.example.com"},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["event_type"] == "browser_login_success"


def test_result_metadata_upload(client, seeded_db):
    """result metadata 업로드가 성공해야 한다."""
    rt = _first_planned_task(seeded_db)
    resp = client.post(
        f"/api/v1/run-tasks/{rt.run_task_id}/result",
        json={
            "employee_id": rt.employee_id,
            "location_id": rt.work_location_id,
            "result_root_path": f"/data/zt/results/{DATE_STR}/{rt.employee_id}/task-001",
            "screenshots_path": f"/data/zt/results/{DATE_STR}/{rt.employee_id}/task-001/screenshots",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "result_root_path" in data
