from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    CONTROLLER_DB_URL: str = "sqlite:///./controller.db"
    CONTROLLER_TIMEZONE: str = "Asia/Seoul"
    DAILY_PLAN_GENERATION_HOUR: int = 6
    TASK_SEED_FILE: str = "./config/tasks.yaml"
    EMPLOYEE_SEED_FILE: str = "./config/employees.yaml"
    LOCATION_SEED_FILE: str = "./config/locations.yaml"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
