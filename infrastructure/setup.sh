#!/usr/bin/env bash
# FadeReach — canonical single-host Docker bootstrap
# Tinlance Limited
#
# This script deliberately does NOT install host PostgreSQL, Redis, Listmonk,
# or n8n. Those services are containerized by docker-compose.yml. Keeping one
# topology avoids split-brain state and port collisions.
#
# Run from the repository checkout:
#   sudo bash infrastructure/setup.sh
#
# After DNS is ready, issue TLS with:
#   sudo certbot --nginx -d fadereach.app -d www.fadereach.app

set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOMAIN="${DOMAIN:-fadereach.app}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@${DOMAIN}}"

log() { printf '[FadeReach] %s\n' "$*"; }
die() { printf '[FadeReach][ERROR] %s\n' "$*" >&2; exit 1; }

[[ "$(id -u)" -eq 0 ]] || die "Run as root (sudo)."
command -v openssl >/dev/null 2>&1 || die "openssl is required."

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends   ca-certificates curl git nginx certbot python3-certbot-nginx ufw fail2ban

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker

docker compose version >/dev/null 2>&1 || die "Docker Compose v2 is required."

install -d -m 0750 /opt/fadereach /opt/fadereach/tenants
chown -R root:root /opt/fadereach

ENV_FILE="$APP_DIR/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  umask 077
  cat > "$ENV_FILE" <<EOF
DOMAIN=$DOMAIN
POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d '=+/\n' | cut -c1-32)
POSTGRES_RUNTIME_PASSWORD=$(openssl rand -base64 32 | tr -d '=+/\n' | cut -c1-32)
N8N_DB_PASSWORD=$(openssl rand -base64 32 | tr -d '=+/\n' | cut -c1-32)
LISTMONK_DB_PASSWORD=$(openssl rand -base64 32 | tr -d '=+/\n' | cut -c1-32)
JWT_SECRET=$(openssl rand -base64 64 | tr -d '=+/\n' | cut -c1-64)
CREDENTIAL_ENCRYPTION_KEY=$(python3 - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
)
N8N_ENCRYPTION_KEY=$(openssl rand -hex 32)
LISTMONK_ADMIN_PASSWORD=$(openssl rand -base64 32 | tr -d '=+/\n' | cut -c1-32)
EOF
  chmod 600 "$ENV_FILE"
  log "Created $ENV_FILE with generated infrastructure secrets."
else
  chmod 600 "$ENV_FILE"
fi

cd "$APP_DIR"
test -f docker-compose.yml || die "docker-compose.yml not found."
test -f infrastructure/postgres/init/01-databases.sh || die "PostgreSQL init script not found."

# The compose project owns PostgreSQL/Redis/n8n/Listmonk. Do not start
# competing host services.
docker compose --env-file "$ENV_FILE" config --quiet
docker compose --env-file "$ENV_FILE" up -d --remove-orphans

cat > /etc/nginx/sites-available/fadereach <<EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

ln -sfn /etc/nginx/sites-available/fadereach /etc/nginx/sites-enabled/fadereach
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable --now nginx

ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

cat > /etc/fail2ban/jail.d/fadereach.local <<'EOF'
[sshd]
enabled = true
EOF
systemctl enable --now fail2ban

log "Waiting for API health."
for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8000/api/health >/tmp/fadereach-health.json; then
    cat /tmp/fadereach-health.json
    log "FadeReach bootstrap completed."
    exit 0
  fi
  sleep 5
done

docker compose --env-file "$ENV_FILE" ps
docker compose --env-file "$ENV_FILE" logs --tail=100 api
die "API health check failed."
