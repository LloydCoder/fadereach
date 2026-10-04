#!/bin/sh
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"   --variable=runtime_password="$POSTGRES_RUNTIME_PASSWORD" <<'SQL'
SELECT format('CREATE ROLE fadereach_runtime LOGIN PASSWORD %L', :'runtime_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'fadereach_runtime')
\gexec

GRANT CONNECT ON DATABASE fadereach_meta TO fadereach_runtime;
GRANT USAGE ON SCHEMA public TO fadereach_runtime;
SQL
