# ZT Controller

Zero Trust 직원 트래픽 시뮬레이션 시스템의 Controller 서비스입니다.

## 역할

- 매일 06:00 하루 업무 계획(daily plan) 생성
- 직원 container가 자신의 `employee_id` / `location_id`로 오늘의 plan을 가져가는 API 제공
- Cafe 야외 근무 dispatch 규칙 적용 (각 Cafe VPC 30% 확률)
- task 상태 / result metadata 수신 및 저장
- 브라우저 자동화·Docker 실행·AWS 인프라를 직접 조작하지 않음

---

## 빠른 시작

```bash
cd controller

# 1) 의존성 설치
pip install -e ".[test]"

# 2) DB 초기화
python scripts/init_db.py

# 3) Seed 데이터 로딩
python scripts/seed_data.py

# 4) API 서버 실행
uvicorn app.main:app --host 0.0.0.0 --port 8443 --reload
```

또는 한 번에:
```bash
bash scripts/run_dev.sh
```

---

## 환경변수

| 변수명 | 기본값 | 설명 |
|---|---|---|
| `CONTROLLER_DB_URL` | `sqlite:///./controller.db` | DB URL (SQLite / PostgreSQL) |
| `CONTROLLER_TIMEZONE` | `Asia/Seoul` | 시간대 |
| `DAILY_PLAN_GENERATION_HOUR` | `6` | 자동 plan 생성 시각(시) |
| `TASK_SEED_FILE` | `./config/tasks.yaml` | task 정의 YAML 경로 |
| `EMPLOYEE_SEED_FILE` | `./config/employees.yaml` | 직원 seed YAML 경로 |
| `LOCATION_SEED_FILE` | `./config/locations.yaml` | location seed YAML 경로 |

`.env` 파일로도 설정 가능합니다.

---

## Seed 데이터 로딩

```bash
# YAML → DB 반영 (upsert)
python scripts/seed_data.py

# 또는 API 호출
curl -X POST http://localhost:8443/api/v1/admin/seed/reload```

---

## Daily Plan 생성

```bash
# 오늘 날짜
python scripts/generate_daily_plan.py

# 특정 날짜
python scripts/generate_daily_plan.py --date 2026-04-27

# 강제 재생성 (실행 중인 task가 없을 때만)
python scripts/generate_daily_plan.py --date 2026-04-27 --force
```

API로도 생성 가능:
```bash
curl -X POST http://localhost:8443/api/v1/admin/daily-plans/generate \
  -H "Content-Type: application/json" \
  -d '{"work_date": "2026-04-27", "force": false}'
```

---

## API 예시

### 헬스 체크 (토큰 불필요)
```bash
curl http://localhost:8443/api/v1/health
```

### 직원 container가 오늘 plan 요청
```bash
# 이 위치에서 일해야 하는지 확인
curl "http://localhost:8443/api/v1/employees/enter-hr-staff/plans/today?location_id=enterprise-hr"```

응답 예시 (이 위치에서 근무):
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
    }
  ]
}
```

응답 예시 (카페 배정으로 이 위치에서 미근무):
```json
{
  "work_date": "2026-04-27",
  "employee_id": "enter-hr-staff",
  "requested_location_id": "enterprise-hr",
  "assigned_location_id": "outdoor-cafe-2",
  "should_work_here": false,
  "tasks": []
}
```

### 특정 날짜 plan 조회
```bash
curl "http://localhost:8443/api/v1/employees/enter-hr-staff/plans/2026-04-27?location_id=enterprise-hr"```

---

## Task 상태 업데이트

```bash
# running 상태로 변경
curl -X POST http://localhost:8443/api/v1/run-tasks/20260427-enter-hr-staff-001/status \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": "enter-hr-staff",
    "location_id": "enterprise-hr",
    "status": "running"
  }'

# 완료 처리
curl -X POST http://localhost:8443/api/v1/run-tasks/20260427-enter-hr-staff-001/status \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": "enter-hr-staff",
    "location_id": "enterprise-hr",
    "status": "succeeded",
    "result_path": "/data/zt/results/2026-04-27/enter-hr-staff/task-001"
  }'
```

## Event / Result Metadata 업로드

```bash
# 이벤트 업로드
curl -X POST http://localhost:8443/api/v1/run-tasks/20260427-enter-hr-staff-001/events \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": "enter-hr-staff",
    "location_id": "enterprise-hr",
    "event_type": "browser_login_success",
    "message": "Login succeeded",
    "payload": {}
  }'

# Result metadata 업로드
curl -X POST http://localhost:8443/api/v1/run-tasks/20260427-enter-hr-staff-001/result \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": "enter-hr-staff",
    "location_id": "enterprise-hr",
    "result_root_path": "/data/zt/results/2026-04-27/enter-hr-staff/task-001",
    "screenshots_path": "/data/zt/results/2026-04-27/enter-hr-staff/task-001/screenshots",
    "browser_trace_path": null,
    "network_log_path": null,
    "metadata": {}
  }'
```

---

## DB

- **기본**: SQLite (`controller.db`)
- **PostgreSQL 마이그레이션**: `CONTROLLER_DB_URL=postgresql://user:pass@host/dbname` 환경변수만 변경
  - SQLAlchemy ORM 기반이므로 코드 변경 없이 전환 가능
  - PostgreSQL 사용 시 `psycopg2-binary` 또는 `asyncpg` 패키지 추가 필요

---

## 테스트

```bash
cd controller
pytest tests/ -v
```
