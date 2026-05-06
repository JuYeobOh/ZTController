"""Phase A10 통합 dry-run.

운영 시나리오를 in-process FastAPI TestClient로 한 싸이클 검증한다.
실 컨테이너/EC2를 띄우지 않고도 Controller-Agent 통합점이 모두 작동하는지 확인.

검증하는 것:
1. health (인증 없이 통과)
2. daily plan 생성 (token 없이 admin API 호출)
3. 어떤 직원이라도 should_work_here=true를 받는다
4. 그 직원의 plan에서 clock_in / work(있다면) / clock_out task가 받아진다
5. clock_in 태스크의 상태 전이: planned → running → succeeded
6. cafe 배정된 직원은 home_location에서 should_work_here=false를 받는다
"""
from __future__ import annotations

from datetime import date

from app.services.daily_plan import generate_daily_plan


def test_dry_run_full_employee_cycle(client, seeded_db):
    work_date = date.today()

    # 1) health
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    # 2) daily plan 생성 (admin API, 토큰 없이)
    r = client.post(
        "/api/v1/admin/daily-plans/generate",
        json={"work_date": str(work_date), "force": False},
    )
    assert r.status_code == 200, r.text
    summary = r.json()
    assert summary["total_employees"] >= 1
    assert summary["total_run_tasks"] >= summary["total_employees"]  # 직원 1명당 ≥ clock_in+clock_out

    # 3) 첫 직원의 home_location에서 plan fetch
    first_assignment = next(
        a for a in summary["assignments"] if not a["is_cafe_dispatch"]
    )
    eid = first_assignment["employee_id"]
    home = first_assignment["home_location_id"]

    r = client.get(f"/api/v1/employees/{eid}/plans/today?location_id={home}")
    assert r.status_code == 200, r.text
    plan = r.json()
    assert plan["should_work_here"] is True
    assert len(plan["tasks"]) >= 2  # clock_in + clock_out 최소

    # 4) clock_in 태스크 상태 전이
    clock_in = next(t for t in plan["tasks"] if t["task_type"] == "clock_in")
    rt_id = clock_in["run_task_id"]

    # planned → running
    r = client.post(
        f"/api/v1/run-tasks/{rt_id}/status",
        json={"employee_id": eid, "location_id": home, "status": "running"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "running"
    assert r.json()["started_at"] is not None

    # running → succeeded
    r = client.post(
        f"/api/v1/run-tasks/{rt_id}/status",
        json={"employee_id": eid, "location_id": home, "status": "succeeded"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "succeeded"
    assert r.json()["completed_at"] is not None

    # 5) result 메타데이터 업로드
    r = client.post(
        f"/api/v1/run-tasks/{rt_id}/result",
        json={
            "employee_id": eid,
            "location_id": home,
            "result_root_path": f"/app/results/{rt_id}",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["result_root_path"] == f"/app/results/{rt_id}"


def test_dry_run_cafe_dispatch_creates_should_not_work_here(seeded_db, client):
    """카페 배정이 발생한 날짜의 시드를 골라 cafe dispatch가 1명 이상 발생할 때
    그 직원이 home_location에서 should_work_here=false 를 받는지 확인."""
    # cafe dispatch가 발생할 때까지 며칠치 시드를 시도. 30%×2 cafes = 평균 0.6명/일,
    # 7일 시도하면 cafe dispatch가 적어도 1번은 발생할 확률이 매우 높다.
    from datetime import timedelta

    target_date = None
    cafe_dispatch_eid = None
    home_location = None
    for offset in range(7):
        d = date.today() + timedelta(days=offset + 1)  # 내일부터
        summary = generate_daily_plan(d, seeded_db, force=False)
        # summary["assignments"]는 DailyAssignment ORM 객체 리스트
        cafe = [a for a in summary["assignments"] if a.is_cafe_dispatch]
        if cafe:
            target_date = d
            cafe_dispatch_eid = cafe[0].employee_id
            home_location = cafe[0].home_location_id
            break

    if target_date is None:
        # 7일 안에 발생 안 했으면 skip (확률적으로 거의 없음)
        import pytest
        pytest.skip("No cafe dispatch in 7-day seed sample")

    # cafe 직원의 home_location에서 fetch → should_work_here=false
    r = client.get(
        f"/api/v1/employees/{cafe_dispatch_eid}/plans/{target_date}"
        f"?location_id={home_location}"
    )
    assert r.status_code == 200, r.text
    plan = r.json()
    assert plan["should_work_here"] is False
    assert plan["tasks"] == []
    assert plan["assigned_location_id"].startswith("outdoor-cafe-")
