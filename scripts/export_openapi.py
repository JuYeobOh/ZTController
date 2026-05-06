#!/usr/bin/env python3
"""OpenAPI 스펙을 docs/ 디렉토리에 JSON/YAML로 내보내는 스크립트."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.models  # noqa: F401
from app.main import app

DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")
os.makedirs(DOCS_DIR, exist_ok=True)

schema = app.openapi()

json_path = os.path.join(DOCS_DIR, "openapi.json")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(schema, f, ensure_ascii=False, indent=2)
print(f"Exported: {json_path}")

try:
    import yaml
    yaml_path = os.path.join(DOCS_DIR, "openapi.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(schema, f, allow_unicode=True, sort_keys=False)
    print(f"Exported: {yaml_path}")
except ImportError:
    print("PyYAML not found, skipping .yaml export")

print("\n서버 실행 후 브라우저에서 확인:")
print("  Swagger UI : http://localhost:8443/docs")
print("  ReDoc      : http://localhost:8443/redoc")
print("  Raw JSON   : http://localhost:8443/openapi.json")
