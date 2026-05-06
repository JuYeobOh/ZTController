from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String, nullable=False)
    secret_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    department: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    home_location_id: Mapped[str] = mapped_column(String, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    eligible_for_cafe: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    vpc_name: Mapped[str | None] = mapped_column(String, nullable=True)
    subnet_name: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )


class DailyAssignment(Base):
    __tablename__ = "daily_assignments"
    __table_args__ = (UniqueConstraint("work_date", "employee_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    employee_id: Mapped[str] = mapped_column(String, nullable=False)
    home_location_id: Mapped[str] = mapped_column(String, nullable=False)
    work_location_id: Mapped[str] = mapped_column(String, nullable=False)
    is_cafe_dispatch: Mapped[bool] = mapped_column(Boolean, default=False)
    cafe_location_id: Mapped[str | None] = mapped_column(String, nullable=True)
    # UTC naive datetimes (stored as UTC, returned as KST in API)
    clock_in_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    clock_out_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    random_seed: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class TaskDefinition(Base):
    __tablename__ = "task_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    site: Mapped[str] = mapped_column(String, nullable=False)
    module: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    params_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )


class RunTask(Base):
    __tablename__ = "run_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_task_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    task_id: Mapped[str] = mapped_column(String, nullable=False)
    employee_id: Mapped[str] = mapped_column(String, nullable=False)
    home_location_id: Mapped[str] = mapped_column(String, nullable=False)
    work_location_id: Mapped[str] = mapped_column(String, nullable=False)
    # clock_in | work | clock_out
    task_type: Mapped[str] = mapped_column(String, nullable=False)
    site: Mapped[str | None] = mapped_column(String, nullable=True)
    module: Mapped[str | None] = mapped_column(String, nullable=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    params_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # UTC naive datetime
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # planned | running | succeeded | failed | skipped | cancelled
    status: Mapped[str] = mapped_column(String, default="planned")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    result_path: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )


class TaskEvent(Base):
    __tablename__ = "task_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_task_id: Mapped[str] = mapped_column(String, nullable=False)
    employee_id: Mapped[str] = mapped_column(String, nullable=False)
    location_id: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str | None] = mapped_column(String, nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class ResultMetadata(Base):
    __tablename__ = "result_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_task_id: Mapped[str] = mapped_column(String, nullable=False)
    employee_id: Mapped[str] = mapped_column(String, nullable=False)
    location_id: Mapped[str] = mapped_column(String, nullable=False)
    result_root_path: Mapped[str] = mapped_column(String, nullable=False)
    screenshots_path: Mapped[str | None] = mapped_column(String, nullable=True)
    browser_trace_path: Mapped[str | None] = mapped_column(String, nullable=True)
    network_log_path: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
