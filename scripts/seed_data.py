#!/usr/bin/env python3
"""YAML seed 데이터를 DB에 로딩하는 스크립트."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.models  # noqa: F401 – 모델 등록
from app.database import SessionLocal, init_db
from app.config import settings
from app.services.seed_loader import reload_seed

if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    try:
        counts = reload_seed(
            db,
            settings.EMPLOYEE_SEED_FILE,
            settings.LOCATION_SEED_FILE,
            settings.TASK_SEED_FILE,
        )
        print(f"Seed loaded: {counts}")
    finally:
        db.close()
