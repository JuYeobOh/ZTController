from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI

from app.config import settings
from app.database import SessionLocal, init_db
from app.routers import admin, employee_plans, health, run_tasks
from app.services.daily_plan import generate_daily_plan
from app.services.seed_loader import reload_seed
from app.utils.time import kst_now

# uvicorn은 자기 logger만 설정하므로 app.* / apscheduler.* logger도 stdout으로
# 찍히게 root에 handler 강제 부착. force=True로 uvicorn의 root 설정도 덮어씀.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    force=True,
)

logger = logging.getLogger(__name__)


def _run_daily_plan_job() -> None:
    db = SessionLocal()
    try:
        # KST 기준 today. OS TZ에 의존하지 않도록 명시.
        today = kst_now().date()
        generate_daily_plan(today, db)
        logger.info("Daily plan generated for %s", today)
    except Exception as exc:
        logger.error("Daily plan generation failed: %s", exc)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # DB 테이블 생성
    import app.models  # noqa: F401
    init_db()

    # Seed 데이터 로드 (upsert — 재시작해도 안전)
    db = SessionLocal()
    try:
        reload_seed(
            db,
            settings.EMPLOYEE_SEED_FILE,
            settings.LOCATION_SEED_FILE,
            settings.TASK_SEED_FILE,
        )
    finally:
        db.close()

    # 스케줄러: 매일 DAILY_PLAN_GENERATION_HOUR시 정각 plan 생성
    scheduler = BackgroundScheduler(timezone=settings.CONTROLLER_TIMEZONE)
    scheduler.add_job(
        _run_daily_plan_job,
        CronTrigger(
            hour=settings.DAILY_PLAN_GENERATION_HOUR,
            minute=0,
            timezone=settings.CONTROLLER_TIMEZONE,
        ),
        misfire_grace_time=3600,
    )
    scheduler.start()
    logger.info(
        "Scheduler started — daily plan at %02d:00 %s",
        settings.DAILY_PLAN_GENERATION_HOUR,
        settings.CONTROLLER_TIMEZONE,
    )

    yield

    scheduler.shutdown()
    logger.info("Scheduler stopped")


app = FastAPI(
    title="ZT Controller",
    description="Zero Trust Employee Traffic Simulation Controller",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(employee_plans.router, prefix="/api/v1")
app.include_router(run_tasks.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
