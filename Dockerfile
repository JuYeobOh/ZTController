FROM python:3.11-slim

# tzdata: APScheduler가 Asia/Seoul cron을 정확히 트리거하려면 필요.
# curl: docker-compose healthcheck 용.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata curl \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/share/zoneinfo/Asia/Seoul /etc/localtime \
    && echo "Asia/Seoul" > /etc/timezone

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

RUN mkdir -p /app/data

# 기본값만 설정
ENV CONTROLLER_DB_URL=sqlite:///./data/controller.db \
    CONTROLLER_TIMEZONE=Asia/Seoul \
    DAILY_PLAN_GENERATION_HOUR=6 \
    TASK_SEED_FILE=./config/tasks.yaml \
    EMPLOYEE_SEED_FILE=./config/employees.yaml \
    LOCATION_SEED_FILE=./config/locations.yaml

EXPOSE 8443

# private VPC 시뮬 환경이라 root로 실행 (호스트 mount 폴더 권한 호환).
# 운영 환경에서는 호스트 폴더 chown으로 비-root 실행 권장.

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8443"]
