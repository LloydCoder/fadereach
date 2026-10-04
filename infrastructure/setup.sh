#!/usr/bin/env bash
# FadeReach production host bootstrap.
# Canonical topology: Docker Compose + host Nginx/Certbot + UFW/Fail2Ban.
# This script deliberately does not install a second host PostgreSQL/Redis/Postfix
# stack or grant the public API access to the Docker socket.
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/fadereach}"
REPO_URL="${REPO_URL:-https://github.com/LloydCoder/fadereach.git}"
DOMAIN="${DOMAIN:-fadereach.app}"

log() { printf '[FadeReach] %s\n' "$*"; }
die() { printf '[FadeReach] ERROR: %s\n' "$*" >&2; exit 1; }

if [[ "${EUID}" -ne 0 ]]; then
  die "Run as root: sudo bash infrastructure/setup.sh"
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq ca-certificates curl fail2ban git nginx ufw openssl python3

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi

docker compose version >/dev/null 2>&1 || die "Docker Compose plugin is required"

install -d -m 0750 "$APP_DIR"

if [[ ! -d "$APP_DIR/.git" ]]; then
  git clone "$REPO_URL" "$APP_DIR"
else
  git -C "$APP_DIR" fetch origin main
  git -C "$APP_DIR" checkout main
  git -C "$APP_DIR" reset --hard origin/main
fi

cd "$APP_DIR"

if [[ ! -f .env ]]; then
  cp .env.example .env
  sed -i "s|^VPS_IP=.*|VPS_IP=$(curl -fsS https://api.ipify.org || true)|" .env
  sed -i "s|^DOMAIN=.*|DOMAIN=$DOMAIN|" .env
  sed -i "s|^APP_URL=.*|APP_URL=https://$DOMAIN|" .env
  sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -d '=+/\\n' | cut -c1-32)|" .env
  sed -i "s|^POSTGRES_RUNTIME_PASSWORD=.*|POSTGRES_RUNTIME_PASSWORD=$(openssl rand -base64 24 | tr -d '=+/\\n' | cut -c1-32)|" .env
  sed -i "s|^JWT_SECRET=.*|JWT_SECRET=$(openssl rand -base64 48 | tr -d '=+/\\n' | cut -c1-64)|" .env
  sed -i "s|^LISTMONK_ADMIN_PASSWORD=.*|LISTMONK_ADMIN_PASSWORD=$(openssl rand -base64 24 | tr -d '=+/\\n' | cut -c1-32)|" .env
  sed -i "s|^N8N_ENCRYPTION_KEY=.*|N8N_ENCRYPTION_KEY=$(openssl rand -base64 32 | tr -d '=+/\\n' | cut -c1-32)|" .env
  CRED_KEY=$(python3 -c 'import base64,os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())')
  sed -i "s|^CREDENTIAL_ENCRYPTION_KEY=.*|CREDENTIAL_ENCRYPTION_KEY=$CRED_KEY|" .env
  chmod 600 .env
  log "Created production .env with generated core secrets. Add optional provider keys before sending."
fi

# Only expose SSH/HTTP/HTTPS at the host edge. SMTP is not part of the current
# FadeReach Compose execution path and must be added only with a separately
# reviewed mail-server architecture.
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

systemctl enable --now fail2ban
systemctl enable --now nginx

# HTTP bootstrap. Certbot can add TLS after DNS points at this host.
cat >/etc/nginx/sites-available/fadereach <<NGINX
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
NGINX

ln -sfn /etc/nginx/sites-available/fadereach /etc/nginx/sites-enabled/fadereach
nginx -t
systemctl reload nginx

docker compose --env-file .env config --quiet
docker compose --env-file .env pull
docker compose --env-file .env up -d --remove-orphans

for _ in $(seq 1 36); do
  if curl -fsS http://127.0.0.1:8000/api/health >/tmp/fadereach-health.json; then
    cat /tmp/fadereach-health.json
    log "FadeReach production stack is healthy."
    exit 0
  fi
  sleep 5
done

docker compose --env-file .env ps
docker compose --env-file .env logs --tail=100 api
exit 1
