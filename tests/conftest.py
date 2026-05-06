"""공통 pytest 픽스처."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 – 모델 등록
from app.database import Base, get_db
from app.main import app
from app.services.seed_loader import reload_seed

_EMPLOYEES_YAML = os.path.join(os.path.dirname(__file__), "../config/employees.yaml")
_LOCATIONS_YAML = os.path.join(os.path.dirname(__file__), "../config/locations.yaml")
_TASKS_YAML = os.path.join(os.path.dirname(__file__), "../config/tasks.yaml")


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture()
def seeded_db(db):
    """employees / locations / tasks YAML이 로딩된 DB 세션."""
    reload_seed(db, _EMPLOYEES_YAML, _LOCATIONS_YAML, _TASKS_YAML)
    return db


@pytest.fixture()
def client(seeded_db):
    """seeded DB를 사용하는 TestClient."""
    def _override():
        yield seeded_db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
