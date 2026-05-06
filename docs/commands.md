# ZT Controller 명령어 가이드

> **모든 명령어는 `controller/` 디렉토리 안에서 실행합니다.**
> ```powershell
> cd C:\Users\seclab\Desktop\ZTController\controller
> ```

## 공통 설정

```
Base URL : http://localhost:8443/api/v1
인증     : 없음 (네트워크 격리: 직원망 VPC CIDR에서만 접근 가능)
```

> 토큰 인증은 제거되었습니다. 이전에 노출되었던 운영 토큰은 폐기됨.

**PowerShell 공통 변수**

```powershell
$BASE = "http://localhost:8443/api/v1"
```

> 일부 예시에 과거 `$HEADER` 사용 흔적이 남아 있을 수 있습니다 — 헤더는 무시되니
> 그대로 호출해도 동작합니다. 추후 일괄 정리 예정.

---

## 1. 초기 설정

### 환경 파일 생성
```powershell
copy .env.example .env
```

### DB 초기화 (테이블 생성)
```powershell
python scripts/init_db.py
```

### Seed 데이터 로드 (직원 / 위치 / 태스크)
```powershell
python scripts/seed_data.py
```
출력 예시: `Seed loaded: {'employees_loaded': 20, 'locations_loaded': 7, 'tasks_loaded': 10}`

---

## 2. 서버 실행

### 직접 실행
```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8443 --reload
```

### Docker Compose
```powershell
docker compose up -d
docker compose down
docker compose logs -f controller
```

---

## 3. 스크립트 명령어

### Daily Plan 생성 (스크립트)
```powershell
# 오늘 날짜
python scripts/generate_daily_plan.py

# 특정 날짜
python scripts/generate_daily_plan.py --date 2026-04-29

# 강제 재생성
python scripts/generate_daily_plan.py --date 2026-04-28 --force
```

### Daily Plan 미리보기 (터미널 테이블)
```powershell
# 오늘 날짜 미리보기
python scripts/preview_daily_plan.py

# 특정 날짜
python scripts/preview_daily_plan.py --date 2026-04-28

# HTML 파일만 출력
python scripts/preview_daily_plan.py --date 2026-04-28 --html-only

# 특정 직원 타임라인
python scripts/preview_daily_plan.py --timeline enter-hr-staff

# 강제 재생성 후 미리보기
python scripts/preview_daily_plan.py --date 2026-04-28 --force
```

### OpenAPI 스펙 내보내기
```powershell
python scripts/export_openapi.py
# 출력: docs/openapi.json, docs/openapi.yaml
```

---

## 4. API - 헬스체크

```powershell
# 토큰 불필요
Invoke-WebRequest -UseBasicParsing "$BASE/health" | Select-Object -ExpandProperty Content
```

---

## 5. API - Admin

### Seed 데이터 리로드
```powershell
Invoke-WebRequest -UseBasicParsing -Method POST "$BASE/admin/seed/reload" -Headers $HEADER | Select-Object -ExpandProperty Content
```

### Daily Plan 생성
```powershell
$body = '{"work_date":"2026-04-28","force":false}' 
Invoke-WebRequest -UseBasicParsing -Method POST "$BASE/admin/daily-plans/generate" `
  -Headers ($HEADER + @{"Content-Type"="application/json"}) `
  -Body $body | Select-Object -ExpandProperty Content
```

강제 재생성:
```powershell
$body = '{"work_date":"2026-04-28","force":true}'
Invoke-WebRequest -UseBasicParsing -Method POST "$BASE/admin/daily-plans/generate" `
  -Headers ($HEADER + @{"Content-Type"="application/json"}) `
  -Body $body | Select-Object -ExpandProperty Content
```

### Daily Plan 조회
```powershell
Invoke-WebRequest -UseBasicParsing "$BASE/admin/daily-plans/2026-04-28" -Headers $HEADER | Select-Object -ExpandProperty Content
```

### Run Task 목록 조회
```powershell
# 전체
Invoke-WebRequest -UseBasicParsing "$BASE/admin/run-tasks" -Headers $HEADER | Select-Object -ExpandProperty Content

# 날짜 필터
Invoke-WebRequest -UseBasicParsing "$BASE/admin/run-tasks?work_date=2026-04-28" -Headers $HEADER | Select-Object -ExpandProperty Content

# 직원 + 날짜 필터
Invoke-WebRequest -UseBasicParsing "$BASE/admin/run-tasks?work_date=2026-04-28&employee_id=enter-hr-staff" -Headers $HEADER | Select-Object -ExpandProperty Content

# 상태 필터 (planned / running / succeeded / failed)
Invoke-WebRequest -UseBasicParsing "$BASE/admin/run-tasks?status=planned" -Headers $HEADER | Select-Object -ExpandProperty Content
```

---

## 6. API - 직원 플랜 조회

### 오늘 플랜 조회
```powershell
Invoke-WebRequest -UseBasicParsing "$BASE/employees/enter-hr-staff/plans/today?location_id=enterprise-hr" -Headers $HEADER | Select-Object -ExpandProperty Content
```

### 날짜 지정 플랜 조회
```powershell
Invoke-WebRequest -UseBasicParsing "$BASE/employees/enter-hr-staff/plans/2026-04-28?location_id=enterprise-hr" -Headers $HEADER | Select-Object -ExpandProperty Content
```

`should_work_here: true` → 해당 위치에서 근무 예정, 태스크 목록 포함  
`should_work_here: false` → 다른 위치 근무 (카페 파견 등), 태스크 없음

---

## 7. API - Run Task 상태/이벤트/결과

### 태스크 상태 업데이트
```powershell
$body = @{
  employee_id = "enter-hr-staff"
  location_id = "enterprise-hr"
  status      = "running"   # planned / running / succeeded / failed
} | ConvertTo-Json

Invoke-WebRequest -UseBasicParsing -Method POST "$BASE/run-tasks/20260428-enter-hr-staff-001/status" `
  -Headers ($HEADER + @{"Content-Type"="application/json"}) `
  -Body $body | Select-Object -ExpandProperty Content
```

### 태스크 이벤트 기록
```powershell
$body = @{
  employee_id = "enter-hr-staff"
  location_id = "enterprise-hr"
  event_type  = "screenshot"
  message     = "로그인 완료"
} | ConvertTo-Json

Invoke-WebRequest -UseBasicParsing -Method POST "$BASE/run-tasks/20260428-enter-hr-staff-001/events" `
  -Headers ($HEADER + @{"Content-Type"="application/json"}) `
  -Body $body | Select-Object -ExpandProperty Content
```

### 태스크 결과 저장
```powershell
$body = @{
  employee_id        = "enter-hr-staff"
  location_id        = "enterprise-hr"
  result_root_path   = "/results/20260428/enter-hr-staff-001"
  screenshots_path   = "/results/20260428/enter-hr-staff-001/screenshots"
} | ConvertTo-Json

Invoke-WebRequest -UseBasicParsing -Method POST "$BASE/run-tasks/20260428-enter-hr-staff-001/result" `
  -Headers ($HEADER + @{"Content-Type"="application/json"}) `
  -Body $body | Select-Object -ExpandProperty Content
```

---

## 8. 테스트

### 전체 테스트 실행
```powershell
python -m pytest
```

### 특정 테스트 파일만
```powershell
python -m pytest tests/test_cafe_dispatch.py -v
```

### 빠른 실행 (출력 최소화)
```powershell
python -m pytest -q
```

---

## 9. 주요 설정값 참조

| 항목 | 위치 | 기본값 |
|------|------|--------|
| DB URL | `.env` → `CONTROLLER_DB_URL` | `sqlite:///./controller.db` |
| 시간대 | `.env` → `CONTROLLER_TIMEZONE` | `Asia/Seoul` |
| 카페 파견 확률 | `app/services/daily_plan.py` → `_CAFE_PROB` | `0.3` (30%) |
| 카페 VPC 목록 | `app/services/daily_plan.py` → `_CAFE_LOCATIONS` | `outdoor-cafe-1`, `outdoor-cafe-2` |
| 작업 간격 | `app/services/daily_plan.py` → `_TASK_GAP_MIN/MAX` | 30분 ~ 60분 |
| 출근 시각 범위 | `app/services/daily_plan.py` | 08:00 ~ 10:00 KST |
| 퇴근 시각 범위 | `app/services/daily_plan.py` | 17:00 ~ 19:00 KST |

---

## 10. Run Task ID 형식

```
{YYYYMMDD}-{employee_id}-{seq:03d}

예시: 20260428-enter-hr-staff-001
      20260428-enter-hr-staff-002
      20260428-enter-hr-staff-003
```

순서: `001` clock_in → `002`~`00N` work tasks → 마지막 clock_out

---

## 11. Docker 빌드 & Docker Hub 배포

### 사전 준비
```powershell
# Docker Hub 로그인
docker login
```

### 이미지 빌드
```powershell
# controller/ 디렉토리에서 실행
docker build -t <dockerhub-username>/zt-controller:latest .

# 버전 태그 추가
docker build -t <dockerhub-username>/zt-controller:v1.0.0 .
```

### Docker Hub 푸시
```powershell
docker push <dockerhub-username>/zt-controller:latest
docker push <dockerhub-username>/zt-controller:v1.0.0
```

### 로컬 테스트 실행
```powershell
docker run -d `
  --name zt-controller `
  --restart always `
  -p 8443:8443 `
  -v ${PWD}/data:/app/data `
  -v ${PWD}/config:/app/config:ro `
  <dockerhub-username>/zt-controller:latest
```

---

## 12. EC2 배포

### EC2 접속 후 Docker 설치 (Amazon Linux 2023)
```bash
sudo yum update -y
sudo yum install -y docker
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker ec2-user
# 이후 재접속 필요
```

### 컨테이너 실행
```bash
# Docker Hub에서 pull 후 실행
docker run -d \
  --name zt-controller \
  --restart always \
  -p 8443:8443 \
  -v /home/ec2-user/zt-data:/app/data \
  <dockerhub-username>/zt-controller:latest
```

### config YAML을 EC2에 직접 올리는 경우
```bash
# 로컬에서 EC2로 config 파일 복사
scp -i key.pem -r ./config ec2-user@<EC2-IP>:/home/ec2-user/zt-config

# 컨테이너 실행 시 마운트
docker run -d \
  --name zt-controller \
  --restart always \
  -p 8443:8443 \
  -v /home/ec2-user/zt-data:/app/data \
  -v /home/ec2-user/zt-config:/app/config:ro \
  <dockerhub-username>/zt-controller:latest
```

### 컨테이너 관리
```bash
# 상태 확인
docker ps

# 로그 확인 (스케줄러 실행 여부 포함)
docker logs zt-controller
docker logs -f zt-controller   # 실시간

# 재시작
docker restart zt-controller

# 이미지 업데이트 (새 버전 배포)
docker pull <dockerhub-username>/zt-controller:latest
docker stop zt-controller && docker rm zt-controller
docker run -d --name zt-controller --restart always \
  -p 8443:8443 \
  -v /home/ec2-user/zt-data:/app/data \
  <dockerhub-username>/zt-controller:latest
```

### EC2 보안 그룹 설정
인바운드 규칙에 아래 포트 추가:

| 포트 | 프로토콜 | 소스 | 용도 |
|------|----------|------|------|
| 8443 | TCP | Agent IP 대역 | API |
| 22   | TCP | 관리자 IP | SSH |

### 헬스체크 (EC2에서)
```bash
curl http://localhost:8443/api/v1/health
```

---

## 13. APScheduler 동작 확인

서버 시작 시 로그에서 스케줄러 확인:
```
INFO:app.main:Scheduler started — daily plan at 06:00 Asia/Seoul
```

매일 06:00 KST에 자동으로 당일 plan이 생성됩니다.  
`DAILY_PLAN_GENERATION_HOUR` 환경변수로 시각 변경 가능:

```bash
# 예: 매일 07:00에 생성
docker run ... -e DAILY_PLAN_GENERATION_HOUR=7 ...
```
