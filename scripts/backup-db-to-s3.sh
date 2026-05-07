#!/usr/bin/env bash
# Controller SQLite DB → S3 백업.
#
# 환경변수 (또는 EnvironmentFile에서):
#   ZT_S3_BUCKET     — 버킷명 (기본: kmuinfosec-lab-zt-testbed-logs)
#   ZT_S3_DB_PREFIX  — 키 prefix (기본: controller-db)
#   DB_HOST_PATH     — DB 파일 경로 (기본: /opt/ZTController/data/controller.db)
#
# systemd timer로 매일 자동 실행 + `systemctl start zt-db-backup.service`로 즉시 실행.
# sqlite3 .backup으로 일관성 snapshot — write lock 짧게 잡아 컨테이너 운영 영향 최소.

set -euo pipefail

DB_HOST_PATH="${DB_HOST_PATH:-/opt/ZTController/data/controller.db}"
S3_BUCKET="${ZT_S3_BUCKET:-kmuinfosec-lab-zt-testbed-logs}"
S3_PREFIX="${ZT_S3_DB_PREFIX:-controller-db}"

if [[ ! -f "$DB_HOST_PATH" ]]; then
    echo "[backup] DB not found: $DB_HOST_PATH" >&2
    exit 1
fi

TS=$(TZ='Asia/Seoul' date +%Y%m%dT%H%M%S)
TMP="/tmp/controller-${TS}.db"

# sqlite3 .backup으로 consistent snapshot 생성.
# 컨테이너의 sqlite 트랜잭션과 충돌 없도록 hot copy 방식.
sqlite3 "$DB_HOST_PATH" ".backup '$TMP'"

aws s3 cp "$TMP" "s3://${S3_BUCKET}/${S3_PREFIX}/controller-${TS}.db" --no-progress

rm -f "$TMP"

echo "[backup $(TZ=Asia/Seoul date -Iseconds)] uploaded: s3://${S3_BUCKET}/${S3_PREFIX}/controller-${TS}.db"
