from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import yaml
from sqlalchemy.orm import Session

from app.models import Employee, Location, TaskDefinition


def _load_yaml(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _upsert_employees(db: Session, records: list[dict]) -> int:
    for rec in records:
        emp = db.query(Employee).filter(Employee.employee_id == rec["employee_id"]).first()
        if emp is None:
            emp = Employee(
                employee_id=rec["employee_id"],
                username=rec.get("username", rec["employee_id"]),
                secret_ref=rec.get("secret_ref"),
                department=rec.get("department", ""),
                role=rec.get("role", ""),
                home_location_id=rec["home_location_id"],
                active=rec.get("active", True),
                eligible_for_cafe=rec.get("eligible_for_cafe", True),
            )
            db.add(emp)
        else:
            emp.username = rec.get("username", rec["employee_id"])
            emp.secret_ref = rec.get("secret_ref")
            emp.department = rec.get("department", "")
            emp.role = rec.get("role", "")
            emp.home_location_id = rec["home_location_id"]
            emp.active = rec.get("active", True)
            emp.eligible_for_cafe = rec.get("eligible_for_cafe", True)
            emp.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.flush()
    return len(records)


def _upsert_locations(db: Session, records: list[dict]) -> int:
    for rec in records:
        loc = db.query(Location).filter(Location.location_id == rec["location_id"]).first()
        if loc is None:
            loc = Location(
                location_id=rec["location_id"],
                vpc_name=rec.get("vpc_name"),
                subnet_name=rec.get("subnet_name"),
                description=rec.get("description"),
            )
            db.add(loc)
        else:
            loc.vpc_name = rec.get("vpc_name")
            loc.subnet_name = rec.get("subnet_name")
            loc.description = rec.get("description")
            loc.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.flush()
    return len(records)


def _upsert_tasks(db: Session, records: list[dict]) -> int:
    for rec in records:
        td = db.query(TaskDefinition).filter(TaskDefinition.task_id == rec["task_id"]).first()
        if td is None:
            td = TaskDefinition(
                task_id=rec["task_id"],
                site=rec["site"],
                module=rec["module"],
                action=rec["action"],
                params_json=rec.get("params"),
                active=rec.get("active", True),
            )
            db.add(td)
        else:
            td.site = rec["site"]
            td.module = rec["module"]
            td.action = rec["action"]
            td.params_json = rec.get("params")
            td.active = rec.get("active", True)
            td.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.flush()
    return len(records)


def reload_seed(
    db: Session,
    employees_file: str,
    locations_file: str,
    tasks_file: str,
) -> dict[str, int]:
    emp_data = _load_yaml(employees_file)
    loc_data = _load_yaml(locations_file)
    task_data = _load_yaml(tasks_file)

    emp_count = _upsert_employees(db, emp_data.get("employees", []))
    loc_count = _upsert_locations(db, loc_data.get("locations", []))
    task_count = _upsert_tasks(db, task_data.get("tasks", []))

    db.commit()
    return {
        "employees_loaded": emp_count,
        "locations_loaded": loc_count,
        "tasks_loaded": task_count,
    }
