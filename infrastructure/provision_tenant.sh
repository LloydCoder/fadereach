#!/bin/bash
# ============================================================
# FadeReach — Tenant Provisioner
# Creates isolated Listmonk Docker instance per SaaS client
# Called by FastAPI on new subscription
# Usage: bash provision_tenant.sh <tenant_id> <tenant_domain> <plan>
# ============================================================

set -e

TENANT_ID=$1
TENANT_DOMAIN=$2
PLAN=$3   # starter | growth | pro

if [[ -z "$TENANT_ID" || -z "$TENANT_DOMAIN" || -z "$PLAN" ]]; then
  echo "Usage: $0 <tenant_id> <tenant_domain> <plan>"
  exit 1
fi

BASE_DIR="/opt/fadereach/tenants"
TENANT_DIR="$BASE_DIR/$TENANT_ID"
NGINX_CONF="/etc/nginx/sites-available/fr-tenant-$TENANT_ID"
LOG="/var/log/fadereach/provisioning.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Plan limits
case $PLAN in
  starter)
    MAX_CONTACTS=2000
    MAX_EMAILS_MONTH=6000
    MAX_DOMAINS=1
    ;;
  growth)
    MAX_CONTACTS=10000
    MAX_EMAILS_MONTH=30000
    MAX_DOMAINS=5
    ;;
  pro)
    MAX_CONTACTS=50000
    MAX_EMAILS_MONTH=150000
    MAX_DOMAINS=15
    ;;
  *)
    echo "Unknown plan: $PLAN"
    exit 1
    ;;
esac

echo "[$DATE] Provisioning tenant: $TENANT_ID | Domain: $TENANT_DOMAIN | Plan: $PLAN" >> $LOG

# ── 1. Generate credentials ──────────────────────────────
DB_NAME="listmonk_$TENANT_ID"
DB_USER="lm_$TENANT_ID"
DB_PASS=$(openssl rand -base64 20 | tr -dc 'a-zA-Z0-9' | head -c 20)
ADMIN_PASS=$(openssl rand -base64 12 | tr -dc 'a-zA-Z0-9' | head -c 12)
PORT=$(python3 -c "import socket; s=socket.socket(); s.bind(('',0)); print(s.getsockname()[1]); s.close()")

echo "[$DATE] Generated port $PORT for $TENANT_ID" >> $LOG

# ── 2. Create PostgreSQL database ────────────────────────
sudo -u postgres psql <<EOF
CREATE DATABASE $DB_NAME;
CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$DB_PASS';
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF

echo "[$DATE] Database $DB_NAME created" >> $LOG

# ── 3. Create tenant directory ───────────────────────────
mkdir -p $TENANT_DIR/{uploads,config}

cat > $TENANT_DIR/docker-compose.yml <<EOF
version: '3.8'

services:
  listmonk-$TENANT_ID:
    image: listmonk/listmonk:latest
    container_name: listmonk-$TENANT_ID
    restart: unless-stopped
    ports:
      - "$PORT:9000"
    environment:
      - LISTMONK_db__host=host.docker.internal
      - LISTMONK_db__port=5432
      - LISTMONK_db__user=$DB_USER
      - LISTMONK_db__password=$DB_PASS
      - LISTMONK_db__database=$DB_NAME
      - LISTMONK_app__address=0.0.0.0:9000
      - LISTMONK_app__admin_username=admin
      - LISTMONK_app__admin_password=$ADMIN_PASS
      # Plan enforcement via env (checked by API layer)
      - FR_PLAN=$PLAN
      - FR_MAX_CONTACTS=$MAX_CONTACTS
      - FR_MAX_EMAILS_MONTH=$MAX_EMAILS_MONTH
      - FR_TENANT_ID=$TENANT_ID
    extra_hosts:
      - "host.docker.internal:host-gateway"
    volumes:
      - $TENANT_DIR/uploads:/listmonk/static/uploads
    labels:
      - "fadereach.tenant=$TENANT_ID"
      - "fadereach.plan=$PLAN"
      - "fadereach.domain=$TENANT_DOMAIN"
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
EOF

# ── 4. Start the container ───────────────────────────────
cd $TENANT_DIR
docker-compose up -d

# Wait for Listmonk to be ready
echo "[$DATE] Waiting for Listmonk to initialize..." >> $LOG
sleep 8
until curl -sf "http://localhost:$PORT/health" > /dev/null 2>&1; do
  sleep 2
done

echo "[$DATE] Listmonk ready on port $PORT" >> $LOG

# ── 5. Configure Nginx routing ───────────────────────────
cat > $NGINX_CONF <<EOF
# FadeReach Tenant: $TENANT_ID
server {
    listen 80;
    server_name $TENANT_ID.fadereach.app;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $TENANT_ID.fadereach.app;

    ssl_certificate /etc/letsencrypt/live/fadereach.app/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/fadereach.app/privkey.pem;

    # Security
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-Content-Type-Options "nosniff";
    add_header Strict-Transport-Security "max-age=31536000";

    # Rate limiting per tenant
    limit_req_zone \$binary_remote_addr zone=$TENANT_ID:10m rate=30r/m;
    limit_req zone=$TENANT_ID burst=10 nodelay;

    location / {
        proxy_pass http://localhost:$PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Tenant-ID $TENANT_ID;
        proxy_read_timeout 60s;
    }
}
EOF

ln -sf $NGINX_CONF /etc/nginx/sites-enabled/
nginx -t && nginx -s reload

echo "[$DATE] Nginx routing configured: $TENANT_ID.fadereach.app → :$PORT" >> $LOG

# ── 6. Save tenant metadata ──────────────────────────────
cat > $TENANT_DIR/config/metadata.json <<EOF
{
  "tenant_id": "$TENANT_ID",
  "domain": "$TENANT_DOMAIN",
  "plan": "$PLAN",
  "port": $PORT,
  "db_name": "$DB_NAME",
  "db_user": "$DB_USER",
  "listmonk_url": "https://$TENANT_ID.fadereach.app",
  "admin_user": "admin",
  "provisioned_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "status": "active",
  "limits": {
    "max_contacts": $MAX_CONTACTS,
    "max_emails_month": $MAX_EMAILS_MONTH,
    "max_domains": $MAX_DOMAINS
  }
}
EOF

# Store credentials securely (hashed in DB, raw in secrets file)
cat >> /root/.fadereach_secrets <<EOF

# Tenant: $TENANT_ID ($DATE)
TENANT_${TENANT_ID}_DB_PASS=$DB_PASS
TENANT_${TENANT_ID}_ADMIN_PASS=$ADMIN_PASS
TENANT_${TENANT_ID}_PORT=$PORT
EOF

echo "[$DATE] ✅ Tenant $TENANT_ID provisioned successfully" >> $LOG

# ── 7. Return JSON for FastAPI ────────────────────────────
cat <<RESULT
{
  "success": true,
  "tenant_id": "$TENANT_ID",
  "listmonk_url": "https://$TENANT_ID.fadereach.app",
  "admin_user": "admin",
  "admin_pass": "$ADMIN_PASS",
  "port": $PORT,
  "plan": "$PLAN"
}
RESULT
