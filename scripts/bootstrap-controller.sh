#!/usr/bin/env bash
# ZeroTrust Controller EC2 부트스트랩 스크립트.
# 빈 Amazon Linux EC2에서 한 번 실행하면 Controller가 8443에서 가동된다.
#
# 사용법:
#   sudo bash bootstrap-controller.sh

set -euo pipefail

GIT_USER="${GIT_USER:-JuYeobOh}"

echo "==[1/4] 패키지 + Docker"
dnf install -y git docker
systemctl enable --now docker

echo "==[2/4] Compose + Buildx 플러그인"
mkdir -p /usr/local/lib/docker/cli-plugins
if [[ ! -x /usr/local/lib/docker/cli-plugins/docker-compose ]]; then
    curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
        -o /usr/local/lib/docker/cli-plugins/docker-compose
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
fi
if [[ ! -x /usr/local/lib/docker/cli-plugins/docker-buildx ]]; then
    curl -SL https://github.com/docker/buildx/releases/download/v0.18.0/buildx-v0.18.0.linux-amd64 \
        -o /usr/local/lib/docker/cli-plugins/docker-buildx
    chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx
fi

echo "==[3/4] ZTController 코드 + .env"
mkdir -p /opt
if [[ ! -d /opt/ZTController/.git ]]; then
    git clone "https://github.com/${GIT_USER}/ZTController.git" /opt/ZTController
fi
cd /opt/ZTController

cat > .env <<'EOF'
CONTROLLER_DB_URL=sqlite:///./data/controller.db
CONTROLLER_TIMEZONE=Asia/Seoul
DAILY_PLAN_GENERATION_HOUR=6
TASK_SEED_FILE=./config/tasks.yaml
EMPLOYEE_SEED_FILE=./config/employees.yaml
LOCATION_SEED_FILE=./config/locations.yaml
EOF

echo "==[4/4] Compose up + 검증"
docker compose up -d --build
sleep 4
docker compose ps
echo "--"
curl -fsS http://localhost:8443/api/v1/health && echo
echo
echo "── DONE ── Controller 가동 중 (port 8443)"
echo "로그 스트림:  docker compose logs -f controller"
echo "오늘 plan 강제 생성:"
echo "  curl -X POST http://localhost:8443/api/v1/admin/daily-plans/generate \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d \"{\\\"work_date\\\":\\\"\$(date +%F)\\\",\\\"force\\\":false}\""
