#!/usr/bin/env python3
"""
Daily plan을 생성하고 터미널 + HTML로 시각화하는 스크립트.

사용법:
  python scripts/preview_daily_plan.py              # 오늘 날짜
  python scripts/preview_daily_plan.py --date 2026-04-27
  python scripts/preview_daily_plan.py --force      # 기존 plan 삭제 후 재생성
  python scripts/preview_daily_plan.py --html-only  # HTML만 생성
"""
import argparse
import os
import sys
from datetime import date, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Windows 콘솔 UTF-8 강제 설정
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import app.models  # noqa: F401
from app.database import SessionLocal, init_db
from app.models import DailyAssignment, RunTask
from app.services.daily_plan import generate_daily_plan

KST = ZoneInfo("Asia/Seoul")
RESET = "\033[0m"
BOLD  = "\033[1m"
RED   = "\033[31m"
GREEN = "\033[32m"
YELLOW= "\033[33m"
CYAN  = "\033[36m"
MAGENTA="\033[35m"

def _kst(dt):
    return dt.replace(tzinfo=timezone.utc).astimezone(KST)

def _fmt(dt):
    return _kst(dt).strftime("%H:%M")

# ── 터미널 출력 ────────────────────────────────────────────────────────────────

def print_summary(work_date, assignments, run_tasks):
    cafe_dispatches = [a for a in assignments if a.is_cafe_dispatch]
    total_tasks = len(run_tasks)

    print(f"\n{BOLD}{'='*72}{RESET}")
    print(f"{BOLD}  ZT Controller - Daily Plan Preview  {work_date}{RESET}")
    print(f"{'='*72}")
    print(f"  직원 수      : {len(assignments)}명")
    print(f"  카페 배정    : {len(cafe_dispatches)}명")
    print(f"  총 run_tasks : {total_tasks}개  "
          f"(직원당 평균 {total_tasks/len(assignments):.1f}개)")

    if cafe_dispatches:
        print(f"\n{YELLOW}{BOLD}  [Cafe Dispatch]{RESET}")
        for a in cafe_dispatches:
            print(f"     {a.employee_id:<28} -> {a.work_location_id}")
    print()

def print_assignments_table(assignments, run_tasks):
    # employee_id → task 수 매핑
    task_counts = {}
    for rt in run_tasks:
        task_counts[rt.employee_id] = task_counts.get(rt.employee_id, 0) + 1

    header = (f"  {'EMPLOYEE':<28} {'HOME':<20} {'WORK':<20} "
              f"{'IN':>5} {'OUT':>5} {'TASKS':>5}")
    print(f"{BOLD}{header}{RESET}")
    print("  " + "-" * 70)

    prev_dept = None
    sorted_assignments = sorted(assignments, key=lambda a: a.employee_id)

    for a in sorted_assignments:
        dept = a.employee_id.rsplit("-", 1)[0]
        if dept != prev_dept:
            print()
            prev_dept = dept

        cafe = a.is_cafe_dispatch
        color = CYAN if cafe else RESET
        cafe_mark = " *" if cafe else "  "
        work_loc = a.work_location_id if not cafe else f"{YELLOW}{a.work_location_id}{RESET}"
        n_tasks = task_counts.get(a.employee_id, 0)

        print(f"  {color}{a.employee_id:<28}{RESET} "
              f"{a.home_location_id:<20} "
              f"{work_loc:<20} "
              f"{_fmt(a.clock_in_at):>5} "
              f"{_fmt(a.clock_out_at):>5} "
              f"{n_tasks:>5}{cafe_mark}")
    print()

def print_task_timeline(employee_id, assignments, run_tasks):
    a = next((x for x in assignments if x.employee_id == employee_id), None)
    if not a:
        print(f"  {employee_id} 없음")
        return

    tasks = sorted(
        [rt for rt in run_tasks if rt.employee_id == employee_id],
        key=lambda rt: rt.scheduled_at,
    )
    ci = _kst(a.clock_in_at)
    co = _kst(a.clock_out_at)
    work_secs = (co - ci).total_seconds()

    print(f"\n{BOLD}  [{employee_id}] 타임라인  "
          f"{ci.strftime('%H:%M')} → {co.strftime('%H:%M')}{RESET}")
    print(f"  work_location: {CYAN if a.is_cafe_dispatch else ''}"
          f"{a.work_location_id}{RESET}\n")

    bar_width = 60
    for rt in tasks:
        t = _kst(rt.scheduled_at)
        offset = (t - ci).total_seconds()
        pos = int(offset / work_secs * bar_width) if work_secs > 0 else 0
        pos = max(0, min(pos, bar_width - 1))
        bar = " " * pos + "^"

        type_colors = {"clock_in": GREEN, "work": RESET, "clock_out": RED}
        c = type_colors.get(rt.task_type, RESET)
        print(f"  {c}{t.strftime('%H:%M')}{RESET} {bar}")
        print(f"         {c}{rt.run_task_id:<40} {rt.task_id}{RESET}")
    print()

# ── HTML 생성 ──────────────────────────────────────────────────────────────────

def _task_rows_html(employee_id, run_tasks):
    tasks = sorted(
        [rt for rt in run_tasks if rt.employee_id == employee_id],
        key=lambda rt: rt.scheduled_at,
    )
    rows = []
    for rt in tasks:
        type_cls = {"clock_in": "type-in", "work": "type-work", "clock_out": "type-out"}
        cls = type_cls.get(rt.task_type, "")
        rows.append(
            f'<tr class="{cls}">'
            f'<td>{rt.run_task_id}</td>'
            f'<td>{rt.task_id}</td>'
            f'<td><span class="badge {cls}">{rt.task_type}</span></td>'
            f'<td>{_fmt(rt.scheduled_at)}</td>'
            f'<td><span class="status">{rt.status}</span></td>'
            f'</tr>'
        )
    return "\n".join(rows)

def _timeline_bar_html(assignments, run_tasks, employee_id):
    a = next((x for x in assignments if x.employee_id == employee_id), None)
    if not a:
        return ""
    tasks = sorted(
        [rt for rt in run_tasks if rt.employee_id == employee_id],
        key=lambda rt: rt.scheduled_at,
    )
    ci = _kst(a.clock_in_at)
    co = _kst(a.clock_out_at)
    work_secs = max((co - ci).total_seconds(), 1)

    dots = []
    for rt in tasks:
        t = _kst(rt.scheduled_at)
        pct = (t - ci).total_seconds() / work_secs * 100
        pct = max(0, min(pct, 100))
        type_cls = {"clock_in": "dot-in", "work": "dot-work", "clock_out": "dot-out"}
        cls = type_cls.get(rt.task_type, "dot-work")
        dots.append(
            f'<div class="dot {cls}" style="left:{pct:.1f}%" '
            f'title="{_fmt(rt.scheduled_at)} {rt.task_id}"></div>'
        )
    return (
        f'<div class="timeline-bar">'
        f'<div class="tl-label">{ci.strftime("%H:%M")}</div>'
        f'<div class="tl-track">{"".join(dots)}</div>'
        f'<div class="tl-label">{co.strftime("%H:%M")}</div>'
        f'</div>'
    )

def generate_html(work_date, assignments, run_tasks, output_path):
    task_counts = {}
    for rt in run_tasks:
        task_counts[rt.employee_id] = task_counts.get(rt.employee_id, 0) + 1

    cafe_dispatches = [a for a in assignments if a.is_cafe_dispatch]
    sorted_assignments = sorted(assignments, key=lambda a: a.employee_id)

    # 직원별 카드
    cards_html = []
    for a in sorted_assignments:
        cafe_badge = '<span class="cafe-badge">☕ Cafe</span>' if a.is_cafe_dispatch else ""
        task_rows = _task_rows_html(a.employee_id, run_tasks)
        timeline = _timeline_bar_html(assignments, run_tasks, a.employee_id)
        n = task_counts.get(a.employee_id, 0)
        cards_html.append(f"""
        <div class="card {'cafe-card' if a.is_cafe_dispatch else ''}">
          <div class="card-header">
            <span class="emp-id">{a.employee_id}</span>
            {cafe_badge}
            <span class="task-count">{n} tasks</span>
          </div>
          <div class="card-meta">
            <span>🏠 {a.home_location_id}</span>
            <span>📍 {a.work_location_id}</span>
            <span>🕗 {_fmt(a.clock_in_at)} ~ {_fmt(a.clock_out_at)}</span>
          </div>
          {timeline}
          <details>
            <summary>Task 목록 ({n}개)</summary>
            <table class="task-table">
              <thead><tr>
                <th>run_task_id</th><th>task_id</th>
                <th>type</th><th>scheduled</th><th>status</th>
              </tr></thead>
              <tbody>{task_rows}</tbody>
            </table>
          </details>
        </div>""")

    cafe_summary = ""
    if cafe_dispatches:
        cafe_items = "".join(
            f'<li><b>{a.work_location_id}</b> → {a.employee_id}</li>'
            for a in cafe_dispatches
        )
        cafe_summary = f'<div class="cafe-summary"><h3>☕ Cafe Dispatch</h3><ul>{cafe_items}</ul></div>'

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>ZT Controller — Daily Plan {work_date}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', sans-serif; background: #0f1117; color: #e0e0e0; padding: 24px; }}
  h1 {{ color: #7eb8f7; margin-bottom: 4px; }}
  .subtitle {{ color: #888; margin-bottom: 20px; font-size: 0.9rem; }}
  .stats {{ display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }}
  .stat {{ background: #1a1d27; border: 1px solid #2a2d3a; border-radius: 8px;
           padding: 12px 20px; min-width: 140px; }}
  .stat-val {{ font-size: 2rem; font-weight: bold; color: #7eb8f7; }}
  .stat-label {{ font-size: 0.8rem; color: #888; margin-top: 2px; }}
  .cafe-summary {{ background: #1e1a10; border: 1px solid #f0a500; border-radius: 8px;
                   padding: 16px; margin-bottom: 24px; }}
  .cafe-summary h3 {{ color: #f0a500; margin-bottom: 8px; }}
  .cafe-summary li {{ margin: 4px 0 4px 16px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(480px, 1fr)); gap: 16px; }}
  .card {{ background: #1a1d27; border: 1px solid #2a2d3a; border-radius: 10px;
           padding: 16px; transition: border-color .2s; }}
  .card:hover {{ border-color: #4a7ec7; }}
  .cafe-card {{ border-color: #f0a500 !important; background: #1e1c14; }}
  .card-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }}
  .emp-id {{ font-weight: bold; font-size: 1rem; color: #c0d8f8; }}
  .cafe-badge {{ background: #f0a500; color: #000; font-size: 0.72rem;
                 padding: 2px 8px; border-radius: 20px; font-weight: bold; }}
  .task-count {{ margin-left: auto; color: #888; font-size: 0.85rem; }}
  .card-meta {{ display: flex; gap: 12px; flex-wrap: wrap; font-size: 0.82rem;
                color: #aaa; margin-bottom: 12px; }}
  .timeline-bar {{ display: flex; align-items: center; gap: 8px; margin: 10px 0 12px; }}
  .tl-label {{ font-size: 0.75rem; color: #888; white-space: nowrap; }}
  .tl-track {{ flex: 1; height: 12px; background: #2a2d3a; border-radius: 6px;
               position: relative; }}
  .dot {{ position: absolute; width: 10px; height: 10px; border-radius: 50%;
          top: 1px; transform: translateX(-50%); cursor: pointer; }}
  .dot-in   {{ background: #4caf50; }}
  .dot-work {{ background: #7eb8f7; }}
  .dot-out  {{ background: #ef5350; }}
  details summary {{ cursor: pointer; color: #7eb8f7; font-size: 0.85rem;
                     margin-bottom: 8px; user-select: none; }}
  .task-table {{ width: 100%; border-collapse: collapse; font-size: 0.8rem; }}
  .task-table th {{ background: #12141e; color: #888; padding: 6px 8px;
                    text-align: left; border-bottom: 1px solid #2a2d3a; }}
  .task-table td {{ padding: 5px 8px; border-bottom: 1px solid #1e2030; }}
  .task-table tr:last-child td {{ border-bottom: none; }}
  .badge {{ padding: 1px 7px; border-radius: 10px; font-size: 0.75rem; }}
  .type-in   .badge {{ background:#1b3d1e; color:#4caf50; }}
  .type-work .badge {{ background:#1a2a3d; color:#7eb8f7; }}
  .type-out  .badge {{ background:#3d1b1b; color:#ef5350; }}
  .status {{ color: #aaa; }}
</style>
</head>
<body>
<h1>ZT Controller — Daily Plan</h1>
<p class="subtitle">생성일: {work_date} &nbsp;|&nbsp; seed: "{work_date}:zt-controller:v1"</p>

<div class="stats">
  <div class="stat"><div class="stat-val">{len(sorted_assignments)}</div><div class="stat-label">총 직원</div></div>
  <div class="stat"><div class="stat-val">{len(cafe_dispatches)}</div><div class="stat-label">카페 배정</div></div>
  <div class="stat"><div class="stat-val">{len(run_tasks)}</div><div class="stat-label">총 run_tasks</div></div>
  <div class="stat"><div class="stat-val">{len(run_tasks)//max(len(sorted_assignments),1)}</div><div class="stat-label">평균 tasks/인</div></div>
</div>

{cafe_summary}

<div class="grid">
{"".join(cards_html)}
</div>
</body>
</html>"""

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Daily plan 생성 + 시각화")
    parser.add_argument("--date", default=str(date.today()), help="YYYY-MM-DD (기본: 오늘)")
    parser.add_argument("--force", action="store_true", help="기존 plan 삭제 후 재생성")
    parser.add_argument("--html-only", action="store_true", help="터미널 출력 없이 HTML만 생성")
    parser.add_argument("--timeline", metavar="EMPLOYEE_ID", help="특정 직원 타임라인 출력")
    args = parser.parse_args()

    work_date = date.fromisoformat(args.date)
    init_db()
    db = SessionLocal()

    try:
        print(f"\n{CYAN}>> {work_date} daily plan 생성 중...{RESET}")
        try:
            generate_daily_plan(work_date, db, force=args.force)
        except ValueError as e:
            print(f"{YELLOW}  (이미 존재: {e}){RESET}")

        assignments = (
            db.query(DailyAssignment).filter(DailyAssignment.work_date == work_date).all()
        )
        run_tasks = db.query(RunTask).filter(RunTask.work_date == work_date).all()

        if not assignments:
            print(f"{RED}  plan이 없습니다. --force 옵션을 사용해보세요.{RESET}")
            return

        if not args.html_only:
            print_summary(work_date, assignments, run_tasks)
            print_assignments_table(assignments, run_tasks)

            if args.timeline:
                print_task_timeline(args.timeline, assignments, run_tasks)

        # HTML 생성
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        html_path = os.path.join(script_dir, "docs", f"plan_{work_date}.html")
        out = generate_html(work_date, assignments, run_tasks, html_path)
        print(f"{GREEN}[OK] HTML 저장됨: {out}{RESET}\n")

    finally:
        db.close()


if __name__ == "__main__":
    main()
