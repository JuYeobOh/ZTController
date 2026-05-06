#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "[1/3] Initializing DB..."
python scripts/init_db.py

echo "[2/3] Loading seed data..."
python scripts/seed_data.py

echo "[3/3] Starting Controller API on port 8443..."
uvicorn app.main:app --host 0.0.0.0 --port 8443 --reload
