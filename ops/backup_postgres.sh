#!/usr/bin/env bash
set -euo pipefail

: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${BACKUP_DIR:=/opt/fadereach/backups}"
: "${POSTGRES_HOST:=127.0.0.1}"
: "${POSTGRES_DB:=fadereach_meta}"
: "${POSTGRES_USER:=fadereach}"

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
tmp="$BACKUP_DIR/fadereach_meta_${stamp}.dump.tmp"
out="$BACKUP_DIR/fadereach_meta_${stamp}.dump"

PGPASSWORD="$POSTGRES_PASSWORD" pg_dump   --host="$POSTGRES_HOST" --username="$POSTGRES_USER" --dbname="$POSTGRES_DB"   --format=custom --no-owner --no-acl --file="$tmp"

mv "$tmp" "$out"
chmod 600 "$out"
sha256sum "$out" > "$out.sha256"
echo "$out"
