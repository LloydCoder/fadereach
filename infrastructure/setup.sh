#!/bin/bash
# ============================================================
# FadeReach — Phase 0 Infrastructure Setup Script
# Tinlance Limited | Lloyd (Chinaemerem Nwachukwu)
# Run on fresh Ubuntu 22.04 VPS (Contabo)
# Usage: sudo bash setup.sh
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()    { echo -e "${GREEN}[FadeReach]${NC} $1"; }
warn()   { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
section(){ echo -e "\n${CYAN}══════════════════════════════════════${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}══════════════════════════════════════${NC}\n"; }

# ── CONFIG — Edit before running ──────────────────────────
DOMAIN="fadereach.app"
SENDING_DOMAIN_1="fr-send1.com"       # Primary sending domain
SENDING_DOMAIN_2="fr-send2.com"       # Secondary rotation domain
VPS_IP="YOUR_VPS_IP"                   # Replace with Contabo IP
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@$DOMAIN}"
POSTGRES_PASSWORD=$(openssl rand -base64 24)
POSTGRES_RUNTIME_PASSWORD=$(openssl rand -base64 24)
JWT_SECRET=$(openssl rand -base64 48)
ADMIN_PASSWORD=$(openssl rand -base64 16)
# ──────────────────────────────────────────────────────────

section "STEP 1 — System Update & Base Packages"
apt-get update -qq && apt-get upgrade -y -qq
apt-get install -y -qq \
  curl wget git unzip \
  nginx certbot python3-certbot-nginx \
  postgresql postgresql-contrib \
  postfix postfix-policyd-spf-python \
  opendkim opendkim-tools \
  fail2ban ufw \
  redis-server \
  build-essential \
  net-tools dnsutils
log "Base packages installed"

section "STEP 2 — Docker & Docker Compose"
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sh
  usermod -aG docker $USER
  log "Docker installed"
else
  log "Docker already present"
fi

if ! command -v docker-compose &>/dev/null; then
  curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
    -o /usr/local/bin/docker-compose
  chmod +x /usr/local/bin/docker-compose
  log "Docker Compose installed"
fi

section "STEP 3 — PostgreSQL Setup"
systemctl start postgresql
systemctl enable postgresql

sudo -u postgres psql <<EOF
-- FadeReach metadata database
CREATE DATABASE fadereach_meta;
CREATE USER fadereach WITH ENCRYPTED PASSWORD '$POSTGRES_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE fadereach_meta TO fadereach;

-- Least-privilege runtime role used by the application
CREATE USER fadereach_runtime WITH ENCRYPTED PASSWORD '$POSTGRES_RUNTIME_PASSWORD';
GRANT CONNECT ON DATABASE fadereach_meta TO fadereach_runtime;

-- Listmonk internal instance (Lloyd's campaigns)
CREATE DATABASE listmonk_internal;
CREATE USER listmonk_internal WITH ENCRYPTED PASSWORD '$POSTGRES_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE listmonk_internal TO listmonk_internal;
EOF

log "PostgreSQL configured"
echo "POSTGRES_PASSWORD=$POSTGRES_PASSWORD" >> /root/.fadereach_secrets

section "STEP 4 — Postfix SMTP Configuration"
cat > /etc/postfix/main.cf <<EOF
# FadeReach Postfix Configuration
# Optimized for cold email deliverability

smtpd_banner = \$myhostname ESMTP
biff = no
append_dot_mydomain = no

# TLS
smtpd_tls_cert_file = /etc/ssl/certs/ssl-cert-snakeoil.pem
smtpd_tls_key_file = /etc/ssl/private/ssl-cert-snakeoil.key
smtpd_use_tls = yes
smtpd_tls_session_cache_database = btree:\${data_directory}/smtpd_scache
smtp_tls_session_cache_database = btree:\${data_directory}/smtp_scache
smtp_tls_security_level = may
smtp_tls_note_starttls_offer = yes

# Hostname
myhostname = mail.$DOMAIN
mydomain = $DOMAIN
myorigin = \$mydomain

# Networks
inet_interfaces = all
inet_protocols = ipv4
mydestination = \$myhostname, localhost.\$mydomain, localhost
relayhost =
mynetworks = 127.0.0.0/8

# Delivery limits — CRITICAL for deliverability
default_destination_concurrency_limit = 2
default_destination_rate_delay = 1s
smtpd_client_connection_rate_limit = 10
smtpd_client_message_rate_limit = 100

# Queue
maximal_queue_lifetime = 1d
bounce_queue_lifetime = 1d
minimal_backoff_time = 300s
maximal_backoff_time = 4000s

# Size
message_size_limit = 10485760
mailbox_size_limit = 0

# DKIM signing
milter_protocol = 6
milter_default_action = accept
smtpd_milters = inet:localhost:8891
non_smtpd_milters = inet:localhost:8891

# Anti-spam
smtpd_helo_required = yes
smtpd_helo_restrictions = permit_mynetworks, reject_invalid_helo_hostname
smtpd_sender_restrictions = permit_mynetworks, reject_non_fqdn_sender
smtpd_recipient_restrictions =
  permit_mynetworks,
  reject_unauth_destination,
  reject_unknown_recipient_domain

# Headers
smtp_header_checks = regexp:/etc/postfix/header_checks
EOF

# Header checks — remove internal routing info
cat > /etc/postfix/header_checks <<EOF
/^Received: .*/    IGNORE
/^X-Originating-IP:/   IGNORE
/^X-Mailer:/       IGNORE
EOF

systemctl restart postfix
log "Postfix configured"

section "STEP 5 — DKIM Setup (OpenDKIM)"
mkdir -p /etc/opendkim/keys/$SENDING_DOMAIN_1
mkdir -p /etc/opendkim/keys/$SENDING_DOMAIN_2

# Generate 2048-bit DKIM keys
opendkim-genkey -b 2048 -d $SENDING_DOMAIN_1 -D /etc/opendkim/keys/$SENDING_DOMAIN_1 -s mail -v
opendkim-genkey -b 2048 -d $SENDING_DOMAIN_2 -D /etc/opendkim/keys/$SENDING_DOMAIN_2 -s mail -v

chown -R opendkim:opendkim /etc/opendkim/keys/

cat > /etc/opendkim.conf <<EOF
Syslog                  yes
SyslogSuccess           yes
LogWhy                  yes
Canonicalization        relaxed/simple
ExternalIgnoreList      refile:/etc/opendkim/TrustedHosts
InternalHosts           refile:/etc/opendkim/TrustedHosts
KeyTable                refile:/etc/opendkim/KeyTable
SigningTable            refile:/etc/opendkim/SigningTable
Mode                    sv
PidFile                 /run/opendkim/opendkim.pid
SignatureAlgorithm      rsa-sha256
UserID                  opendkim
Socket                  inet:8891@localhost
EOF

cat > /etc/opendkim/TrustedHosts <<EOF
127.0.0.1
localhost
$VPS_IP
*.$DOMAIN
*.$SENDING_DOMAIN_1
*.$SENDING_DOMAIN_2
EOF

cat > /etc/opendkim/KeyTable <<EOF
mail._domainkey.$SENDING_DOMAIN_1 $SENDING_DOMAIN_1:mail:/etc/opendkim/keys/$SENDING_DOMAIN_1/mail.private
mail._domainkey.$SENDING_DOMAIN_2 $SENDING_DOMAIN_2:mail:/etc/opendkim/keys/$SENDING_DOMAIN_2/mail.private
EOF

cat > /etc/opendkim/SigningTable <<EOF
*@$SENDING_DOMAIN_1 mail._domainkey.$SENDING_DOMAIN_1
*@$SENDING_DOMAIN_2 mail._domainkey.$SENDING_DOMAIN_2
EOF

systemctl restart opendkim
systemctl enable opendkim
log "DKIM configured with 2048-bit keys"

section "STEP 6 — DNS Records Output"
echo ""
warn "ADD THESE DNS RECORDS IN CLOUDFLARE FOR EACH SENDING DOMAIN:"
echo ""
echo "━━━━━━━━━━━━━━━━ $SENDING_DOMAIN_1 ━━━━━━━━━━━━━━━━"
echo ""
echo "Type  Name              Value"
echo "────  ────────────────  ────────────────────────────────────"
echo "A     @                 $VPS_IP"
echo "A     mail              $VPS_IP"
echo "MX    @                 mail.$SENDING_DOMAIN_1 (priority 10)"
echo "TXT   @                 v=spf1 ip4:$VPS_IP include:_spf.$SENDING_DOMAIN_1 ~all"
echo "TXT   mail._domainkey   $(cat /etc/opendkim/keys/$SENDING_DOMAIN_1/mail.txt | grep -o 'p=.*' | head -1)"
echo "TXT   _dmarc            v=DMARC1; p=none; rua=mailto:dmarc@$SENDING_DOMAIN_1; ruf=mailto:dmarc@$SENDING_DOMAIN_1; fo=1"
echo ""
echo "━━━━━━━━━━━━━━━━ $SENDING_DOMAIN_2 ━━━━━━━━━━━━━━━━"
echo ""
echo "Type  Name              Value"
echo "────  ────────────────  ────────────────────────────────────"
echo "A     @                 $VPS_IP"
echo "A     mail              $VPS_IP"
echo "MX    @                 mail.$SENDING_DOMAIN_2 (priority 10)"
echo "TXT   @                 v=spf1 ip4:$VPS_IP include:_spf.$SENDING_DOMAIN_2 ~all"
echo "TXT   mail._domainkey   $(cat /etc/opendkim/keys/$SENDING_DOMAIN_2/mail.txt | grep -o 'p=.*' | head -1)"
echo "TXT   _dmarc            v=DMARC1; p=none; rua=mailto:dmarc@$SENDING_DOMAIN_2; ruf=mailto:dmarc@$SENDING_DOMAIN_2; fo=1"
echo ""

section "STEP 7 — Firewall (UFW)"
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 25/tcp    # SMTP
ufw allow 587/tcp   # SMTP submission
ufw allow 465/tcp   # SMTPS
ufw --force enable
log "Firewall configured"

section "STEP 8 — Fail2Ban"
cat > /etc/fail2ban/jail.local <<EOF
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true

[postfix]
enabled = true

[nginx-http-auth]
enabled = true
EOF

systemctl restart fail2ban
systemctl enable fail2ban
log "Fail2Ban active"

section "STEP 9 — Nginx Base Configuration"
# Bootstrap with HTTP only. Certbot adds TLS after DNS is ready; this avoids
# referencing certificates that do not exist yet.
cat > /etc/nginx/sites-available/fadereach <<EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
server {
    listen 80;
    server_name campaigns.tinlance.com;
    location / {
        proxy_pass http://127.0.0.1:9100;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

ln -sf /etc/nginx/sites-available/fadereach /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
log "Nginx HTTP bootstrap configured"

section "STEP 10 — Internal Listmonk (Lloyd's Campaigns)"
mkdir -p /opt/fadereach/listmonk-internal
cat > /opt/fadereach/listmonk-internal/docker-compose.yml <<EOF
version: '3.8'

services:
  listmonk:
    image: listmonk/listmonk:latest
    container_name: listmonk-internal
    restart: unless-stopped
    ports:
      - "9100:9000"
    environment:
      - LISTMONK_db__host=host.docker.internal
      - LISTMONK_db__port=5432
      - LISTMONK_db__user=listmonk_internal
      - LISTMONK_db__password=$POSTGRES_PASSWORD
      - LISTMONK_db__database=listmonk_internal
      - LISTMONK_app__address=0.0.0.0:9000
      - LISTMONK_app__admin_username=lloyd
      - LISTMONK_app__admin_password=$ADMIN_PASSWORD
    extra_hosts:
      - "host.docker.internal:host-gateway"
    volumes:
      - ./uploads:/listmonk/static/uploads
EOF

cd /opt/fadereach/listmonk-internal
docker-compose up -d
log "Internal Listmonk running on port 9100"

section "STEP 11 — Warmup Monitor (Cron)"
cat > /opt/fadereach/warmup_monitor.sh <<'WARMUP'
#!/bin/bash
# Daily warmup volume tracker
# Enforces gradual ramp schedule

LOG="/var/log/fadereach/warmup.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Check postfix mail queue
QUEUE=$(mailq | grep -c "^[A-Z0-9]" || echo 0)
# Check today's sent count
SENT=$(grep "$(date '+%b %e')" /var/log/mail.log | grep "status=sent" | wc -l)
# Check bounces
BOUNCED=$(grep "$(date '+%b %e')" /var/log/mail.log | grep "status=bounced" | wc -l)
# Bounce rate alert
if [ "$SENT" -gt 10 ] && [ "$BOUNCED" -gt 0 ]; then
  RATE=$(echo "scale=2; $BOUNCED * 100 / $SENT" | bc)
  if (( $(echo "$RATE > 2.0" | bc -l) )); then
    echo "[$DATE] ALERT: Bounce rate $RATE% — PAUSE CAMPAIGNS" >> $LOG
    # TODO: webhook to dashboard alert
  fi
fi

echo "[$DATE] Sent: $SENT | Bounced: $BOUNCED | Queue: $QUEUE" >> $LOG
WARMUP

chmod +x /opt/fadereach/warmup_monitor.sh
mkdir -p /var/log/fadereach

# Run every hour
(crontab -l 2>/dev/null; echo "0 * * * * /opt/fadereach/warmup_monitor.sh") | crontab -
log "Warmup monitor scheduled (hourly)"

section "STEP 12 — SSL Certificates"
log "Run these commands after DNS propagates (5–30 min):"
echo ""
echo "  certbot --nginx -d $DOMAIN -d www.$DOMAIN --email $ADMIN_EMAIL --agree-tos --non-interactive"
echo "  certbot --nginx -d campaigns.tinlance.com --email $ADMIN_EMAIL --agree-tos --non-interactive"
echo ""

section "STEP 13 — Save Credentials"
cat > /root/.fadereach_secrets <<EOF
# FadeReach Secrets — KEEP PRIVATE
Generated: $(date)

DOMAIN=$DOMAIN
VPS_IP=$VPS_IP
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_RUNTIME_PASSWORD=$POSTGRES_RUNTIME_PASSWORD
JWT_SECRET=$JWT_SECRET
ADMIN_PASSWORD=$ADMIN_PASSWORD
LISTMONK_INTERNAL_URL=http://localhost:9100
LISTMONK_ADMIN_USER=lloyd
LISTMONK_ADMIN_PASS=$ADMIN_PASSWORD
EOF

chmod 600 /root/.fadereach_secrets
log "Credentials saved to /root/.fadereach_secrets"

section "✅ PHASE 0 COMPLETE"
echo ""
echo "  Next steps:"
echo "  1. Add DNS records listed above to Cloudflare"
echo "  2. Wait 10–30 min for DNS propagation"
echo "  3. Run certbot commands for SSL"
echo "  4. Verify: curl https://$DOMAIN"
echo "  5. Access Listmonk: https://campaigns.tinlance.com"
echo "  6. Begin 14-day warmup (5-10 emails/day Week 1)"
echo ""
echo "  Secrets file: /root/.fadereach_secrets"
echo ""
log "FadeReach infrastructure is live. Let's get to inbox. 🚀"
