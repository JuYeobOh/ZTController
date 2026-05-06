#!/usr/bin/env python3
"""DB 테이블 생성 스크립트."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import init_db  # noqa: E402
import app.models  # noqa: E402, F401  – 모델 등록

if __name__ == "__main__":
    init_db()
    print("DB tables created successfully.")
