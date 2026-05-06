# ZT Controller API 문서

Base URL: `http://<controller-host>:8443`

## 인증

토큰 인증은 제거되었습니다. Controller는 SG/NACL로 직원망 VPC CIDR에서만
도달 가능하도록 네트워크 격리되어 있으며, 외부에서는 8443 포트에 접근할 수 없습니다.

> 이 문서의 일부 curl 예시에는 과거 `X-Controller-Token` 헤더가 남아 있을 수 있습니다.
> 헤더는 무시되니 그대로 호출해도 동작합니다 — 추후 일괄 정리 예정.

---

## 목차

1. [Health](#1-health)
2. [Employee Plan — 오늘 plan 요청](#2-employee-plan--오늘-plan-요청)
3. [Employee Plan — 특정 날짜 plan 요청](#3-employee-plan--특정-날짜-plan-요청)
4. [Run Task — 상태 업데이트](#4-run-task--상태-업데이트)
5. [Run Task — 이벤트 업로드](#5-run-task--이벤트-업로드)
6. [Run Task — Result Metadata 업로드](#6-run-task--result-metadata-업로드)
7. [Admin — Daily Plan 생성](#7-admin--daily-plan-생성)
8. [Admin — Daily Plan 조회](#8-admin--daily-plan-조회)
9. [Admin — Run Task 목록 조회](#9-admin--run-task-목록-조회)
10. [Admin — Seed 재로딩](#10-admin--seed-재로딩)

---

## 1. Health

서버 상태 확인. **토큰 불필요**.

```
GET /api/v1/health
```

### 응답 `200`

```json
{
  "status": "ok",
  "time": "2026-04-27T15:30:00+09:00"
}
```

---

## 2. Employee Plan — 오늘 plan 요청

Employee container가 오늘 자신이 이 위치에서 일해야 하는지 확인합니다.

```
GET /api/v1/employees/{employee_id}/plans/today?location_id={location_id}
```

| 파라미터 | 위치 | 필수 | 설명 |
|---|---|---|---|
| `employee_id` | path | ✅ | 직원 ID (예: `enter-hr-staff`) |
| `location_id` | query | ✅ | 현재 실행 중인 location ID |

### 응답 `200` — 이 위치에서 근무

```json
{
  "work_date": "2026-04-27",
  "employee_id": "enter-hr-staff",
  "requested_location_id": "enterprise-hr",
  "assigned_location_id": "enterprise-hr",
  "should_work_here": true,
  "clock_in_at": "2026-04-27T08:35:00+09:00",
  "clock_out_at": "2026-04-27T17:45:00+09:00",
  "tasks": [
    {
      "run_task_id": "20260427-enter-hr-staff-001",
      "task_id": "attendance-clock-in",
      "task_type": "clock_in",
      "site": "groupoffice",
      "module": "common",
      "action": "login",
      "scheduled_at": "2026-04-27T08:35:00+09:00",
      "status": "planned"
    },
    {
      "run_task_id": "20260427-enter-hr-staff-002",
      "task_id": "groupoffice-calendar-check",
      "task_type": "work",
      "site": "groupoffice",
      "module": "calendar",
      "action": "switch_view",
      "scheduled_at": "2026-04-27T10:15:00+09:00",
      "status": "planned"
    },
    {
      "run_task_id": "20260427-enter-hr-staff-005",
      "task_id": "attendance-clock-out",
      "task_type": "clock_out",
      "site": "groupoffice",
      "module": "common",
      "action": "logout",
      "scheduled_at": "2026-04-27T17:45:00+09:00",
      "status": "planned"
    }
  ]
}
```

### 응답 `200` — 카페 배정으로 이 위치에서 미근무

```json
{
  "work_date": "2026-04-27",
  "employee_id": "enter-hr-staff",
  "requested_location_id": "enterprise-hr",
  "assigned_location_id": "outdoor-cafe-2",
  "should_work_here": false,
  "clock_in_at": null,
  "clock_out_at": null,
  "tasks": []
}
```

### 응답 `404` — 오늘 plan이 아직 생성되지 않음

```json
{
  "detail": "No daily plan generated for 2026-04-27"
}
```

### `task_type` 값

| 값 | 설명 |
|---|---|
| `clock_in` | 출근 (로그인) 작업 |
| `work` | 업무 작업 |
| `clock_out` | 퇴근 (로그아웃) 작업 |

### `status` 값

| 값 | 설명 |
|---|---|
| `planned` | 예정됨 (초기 상태) |
| `running` | 실행 중 |
| `succeeded` | 성공 완료 |
| `failed` | 실패 |
| `skipped` | 건너뜀 |
| `cancelled` | 취소됨 |

---

## 3. Employee Plan — 특정 날짜 plan 요청

```
GET /api/v1/employees/{employee_id}/plans/{work_date}?location_id={location_id}
```

| 파라미터 | 위치 | 필수 | 설명 |
|---|---|---|---|
| `employee_id` | path | ✅ | 직원 ID |
| `work_date` | path | ✅ | 날짜 (YYYY-MM-DD) |
| `location_id` | query | ✅ | location ID |

응답 형식은 [#2](#2-employee-plan--오늘-plan-요청)와 동일합니다.

---

## 4. Run Task — 상태 업데이트

Task 실행 상태를 Controller에 보고합니다.

```
POST /api/v1/run-tasks/{run_task_id}/status
```

### 요청 바디

```json
{
  "employee_id": "enter-hr-staff",
  "location_id": "enterprise-hr",
  "status": "running",
  "result_path": null,
  "error_message": null,
  "metadata": {}
}
```

| 필드 | 필수 | 설명 |
|---|---|---|
| `employee_id` | ✅ | run_task의 소유 직원과 일치해야 함 |
| `location_id` | ✅ | run_task의 `work_location_id`와 일치해야 함 |
| `status` | ✅ | `running` / `succeeded` / `failed` / `skipped` / `cancelled` |
| `result_path` | ❌ | 결과 파일 경로 (succeeded 시 사용) |
| `error_message` | ❌ | 오류 메시지 (failed 시 사용) |
| `metadata` | ❌ | 추가 메타데이터 (dict) |

### 응답 `200`

```json
{
  "run_task_id": "20260427-enter-hr-staff-001",
  "status": "running",
  "started_at": "2026-04-27T08:35:12+09:00",
  "completed_at": null
}
```

### 오류

| 코드 | 사유 |
|---|---|
| `403` | `employee_id` 또는 `location_id` 불일치 |
| `404` | `run_task_id` 없음 |
| `422` | 유효하지 않은 `status` 값 |

---

## 5. Run Task — 이벤트 업로드

Task 실행 중 발생한 이벤트를 기록합니다.

```
POST /api/v1/run-tasks/{run_task_id}/events
```

### 요청 바디

```json
{
  "employee_id": "enter-hr-staff",
  "location_id": "enterprise-hr",
  "event_type": "browser_login_success",
  "message": "Login succeeded at 08:35",
  "payload": {
    "url": "https://groupoffice.example.com",
    "elapsed_ms": 1240
  }
}
```

### 응답 `200`

```json
{
  "id": 42,
  "run_task_id": "20260427-enter-hr-staff-001",
  "event_type": "browser_login_success",
  "created_at": "2026-04-27T08:35:12+09:00"
}
```

---

## 6. Run Task — Result Metadata 업로드

Task 완료 후 결과 파일 경로 및 메타데이터를 저장합니다.  
실제 파일은 Worker EC2의 EBS에 저장되고, Controller는 경로(path)만 저장합니다.

```
POST /api/v1/run-tasks/{run_task_id}/result
```

### 요청 바디

```json
{
  "employee_id": "enter-hr-staff",
  "location_id": "enterprise-hr",
  "result_root_path": "/data/zt/results/2026-04-27/enter-hr-staff/task-001",
  "screenshots_path": "/data/zt/results/2026-04-27/enter-hr-staff/task-001/screenshots",
  "browser_trace_path": "/data/zt/results/2026-04-27/enter-hr-staff/task-001/trace.zip",
  "network_log_path": null,
  "metadata": {
    "duration_sec": 45,
    "page_title": "GroupOffice Calendar"
  }
}
```

### 응답 `200`

```json
{
  "id": 7,
  "run_task_id": "20260427-enter-hr-staff-001",
  "result_root_path": "/data/zt/results/2026-04-27/enter-hr-staff/task-001"
}
```

---

## 7. Admin — Daily Plan 생성

지정 날짜의 daily plan을 생성합니다.  
매일 06:00에 자동 생성하거나, 이 API로 수동 생성합니다.

```
POST /api/v1/admin/daily-plans/generate
```

### 요청 바디

```json
{
  "work_date": "2026-04-27",
  "force": false
}
```

| 필드 | 설명 |
|---|---|
| `work_date` | 생성 대상 날짜 (YYYY-MM-DD) |
| `force` | `true`이면 기존 plan 삭제 후 재생성. 단, 실행 중/완료된 task가 있으면 거부 |

### 응답 `200`

```json
{
  "work_date": "2026-04-27",
  "total_employees": 20,
  "cafe_dispatches": 2,
  "total_run_tasks": 106,
  "cafe_assignments": {
    "outdoor-cafe-2": "enter-sales-staff",
    "outdoor-cafe-3": "branch-it-manager"
  },
  "assignments": [ ... ],
  "run_tasks": [ ... ]
}
```

### 오류

| 코드 | 사유 |
|---|---|
| `409` | `force=true`이지만 실행 중/완료된 task 존재 |
| `422` | 날짜 형식 오류 |

---

## 8. Admin — Daily Plan 조회

```
GET /api/v1/admin/daily-plans/{work_date}
```

응답 형식은 [#7](#7-admin--daily-plan-생성) 응답과 동일합니다.

---

## 9. Admin — Run Task 목록 조회

```
GET /api/v1/admin/run-tasks?work_date=YYYY-MM-DD&employee_id=&status=
```

| 파라미터 | 필수 | 설명 |
|---|---|---|
| `work_date` | ❌ | 날짜 필터 |
| `employee_id` | ❌ | 직원 필터 |
| `status` | ❌ | 상태 필터 (`planned` / `running` / `succeeded` / `failed` / `skipped` / `cancelled`) |

### 응답 `200`

```json
{
  "total": 5,
  "items": [
    {
      "run_task_id": "20260427-enter-hr-staff-001",
      "employee_id": "enter-hr-staff",
      "task_id": "attendance-clock-in",
      "task_type": "clock_in",
      "site": "groupoffice",
      "module": "common",
      "action": "login",
      "scheduled_at": "2026-04-27T08:35:00+09:00",
      "status": "succeeded"
    }
  ]
}
```

---

## 10. Admin — Seed 재로딩

`config/employees.yaml`, `config/locations.yaml`, `config/tasks.yaml`을 읽어 DB에 반영합니다.  
이미 존재하는 항목은 upsert(업데이트)됩니다.

```
POST /api/v1/admin/seed/reload
```

요청 바디 없음.

### 응답 `200`

```json
{
  "employees_loaded": 20,
  "locations_loaded": 8,
  "tasks_loaded": 10
}
```

---

## 빠른 참조 — curl 예시

```bash
BASE="http://localhost:8443"

# Health
curl "$BASE/api/v1/health"

# 오늘 plan 요청
curl "$BASE/api/v1/employees/enter-hr-staff/plans/today?location_id=enterprise-hr"

# Daily plan 생성
curl -X POST -H "Content-Type: application/json" \
  -d '{"work_date":"2026-04-27","force":false}' \
  "$BASE/api/v1/admin/daily-plans/generate"

# Task 상태 업데이트
curl -X POST -H "Content-Type: application/json" \
  -d '{"employee_id":"enter-hr-staff","location_id":"enterprise-hr","status":"running"}' \
  "$BASE/api/v1/run-tasks/20260427-enter-hr-staff-001/status"

# Seed 재로딩
curl -X POST -H "$H" "$BASE/api/v1/admin/seed/reload"

# 실패한 task 조회
curl -H "$H" "$BASE/api/v1/admin/run-tasks?work_date=2026-04-27&status=failed"
```

---

## 대화형 문서 (서버 실행 후)

| URL | 설명 |
|---|---|
| `http://localhost:8443/docs` | Swagger UI (테스트 가능) |
| `http://localhost:8443/redoc` | ReDoc (읽기 전용) |
| `http://localhost:8443/openapi.json` | Raw OpenAPI JSON |
