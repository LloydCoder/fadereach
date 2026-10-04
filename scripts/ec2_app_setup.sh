#!/bin/bash
# FadeReach production host bootstrap.
# The canonical runtime is Docker Compose; GitHub Actions performs deployments.

set -euo pipefail

APP_DIR="/opt/fadereach"
REPO_URL="https://github.com/LloydCoder/fadereach.git"

echo "[FadeReach] Installing production prerequisites..."
sudo apt-get update -qq
sudo apt-get install -y -qq git curl ca-certificates

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose plugin is required." >&2
  exit 1
fi

if [ ! -d "$APP_DIR/.git" ]; then
  sudo git clone "$REPO_URL" "$APP_DIR"
  sudo chown -R "$USER:$USER" "$APP_DIR"
else
  cd "$APP_DIR"
  git fetch origin main
  git checkout main
  git reset --hard origin/main
fi

cd "$APP_DIR"

if [ ! -f ".env" ]; then
  cp .env.example .env
  chmod 600 .env
  echo "Created $APP_DIR/.env. Populate production secrets before starting the stack." >&2
  exit 1
fi

docker compose --env-file .env config --quiet
docker compose --env-file .env up -d --remove-orphans

for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8000/api/health; then
    echo
    echo "[FadeReach] Production stack is healthy."
    exit 0
  fi
  sleep 5
done

docker compose --env-file .env ps
docker compose --env-file .env logs --tail=100 api
exit 1
