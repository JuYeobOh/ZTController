#!/usr/bin/env python3
"""지정된 날짜의 daily plan을 생성하는 스크립트."""
import argparse
import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.models  # noqa: F401
from app.database import SessionLocal, init_db
from app.services.daily_plan import generate_daily_plan

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate daily plan")
    parser.add_argument("--date", default=str(date.today()), help="YYYY-MM-DD")
    parser.add_argument("--force", action="store_true", help="Force regeneration")
    args = parser.parse_args()

    work_date = date.fromisoformat(args.date)
    init_db()
    db = SessionLocal()
    try:
        summary = generate_daily_plan(work_date, db, force=args.force)
        print(f"Plan generated for {summary['work_date']}")
        print(f"  Employees : {summary['total_employees']}")
        print(f"  Cafe dispatches: {summary['cafe_dispatches']}")
        print(f"  Cafe assignments: {summary['cafe_assignments']}")
        print(f"  Total run_tasks: {summary['total_run_tasks']}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()
