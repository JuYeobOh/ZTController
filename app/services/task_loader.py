from sqlalchemy.orm import Session

from app.models import TaskDefinition

_ATTENDANCE_IDS = {"attendance-clock-in", "attendance-clock-out"}


def get_clock_in_task(db: Session) -> TaskDefinition | None:
    return (
        db.query(TaskDefinition)
        .filter(TaskDefinition.task_id == "attendance-clock-in", TaskDefinition.active == True)
        .first()
    )


def get_clock_out_task(db: Session) -> TaskDefinition | None:
    return (
        db.query(TaskDefinition)
        .filter(TaskDefinition.task_id == "attendance-clock-out", TaskDefinition.active == True)
        .first()
    )


def get_work_tasks(db: Session) -> list[TaskDefinition]:
    return (
        db.query(TaskDefinition)
        .filter(
            TaskDefinition.active == True,
            TaskDefinition.task_id.not_in(_ATTENDANCE_IDS),
        )
        .order_by(TaskDefinition.task_id)
        .all()
    )
