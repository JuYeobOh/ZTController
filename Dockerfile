FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

RUN mkdir -p /app/data && \
    addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser && \
    chown -R appuser:appgroup /app/data

# 기본값만 설정 — 토큰은 반드시 docker run -e 로 주입
ENV CONTROLLER_DB_URL=sqlite:///./data/controller.db \
    CONTROLLER_TIMEZONE=Asia/Seoul \
    DAILY_PLAN_GENERATION_HOUR=6 \
    TASK_SEED_FILE=./config/tasks.yaml \
    EMPLOYEE_SEED_FILE=./config/employees.yaml \
    LOCATION_SEED_FILE=./config/locations.yaml

EXPOSE 8443

USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8443"]
