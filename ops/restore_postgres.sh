#!/usr/bin/env bash
set -euo pipefail

: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${BACKUP_FILE:?BACKUP_FILE is required}"
: "${POSTGRES_HOST:=127.0.0.1}"
: "${POSTGRES_DB:=fadereach_meta}"
: "${POSTGRES_USER:=fadereach}"

test -f "$BACKUP_FILE"
test -f "$BACKUP_FILE.sha256"
sha256sum --check "$BACKUP_FILE.sha256"

echo "WARNING: restore replaces database contents."
read -r -p "Type RESTORE to continue: " confirm
test "$confirm" = "RESTORE"

PGPASSWORD="$POSTGRES_PASSWORD" pg_restore   --clean --if-exists --no-owner --no-acl   --host="$POSTGRES_HOST" --username="$POSTGRES_USER" --dbname="$POSTGRES_DB"   "$BACKUP_FILE"
