from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    CONTROLLER_DB_URL: str = "sqlite:///./controller.db"
    CONTROLLER_TIMEZONE: str = "Asia/Seoul"
    DAILY_PLAN_GENERATION_HOUR: int = 6
    TASK_SEED_FILE: str = "./config/tasks.yaml"
    EMPLOYEE_SEED_FILE: str = "./config/employees.yaml"
    LOCATION_SEED_FILE: str = "./config/locations.yaml"

    # ── 운영 다이얼 (.env에서 조정 가능, restart로 반영) ─────────────
    CAFE_PROBABILITY: float = 0.3            # 각 카페 location당 dispatch 확률
    TASK_GAP_MIN_SECONDS: int = 1800         # work task 사이 최소 간격 (30분)
    TASK_GAP_MAX_SECONDS: int = 3600         # work task 사이 최대 간격 (60분)
    CLOCK_IN_HOUR: int = 8                   # 출근 시작 시각 (시)
    CLOCK_IN_RANGE_HOURS: int = 2            # 출근 분산 폭 (8 ~ 8+2 = 10시)
    CLOCK_OUT_HOUR: int = 17                 # 퇴근 시작 시각 (시)
    CLOCK_OUT_RANGE_HOURS: int = 2           # 퇴근 분산 폭 (17 ~ 17+2 = 19시)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
