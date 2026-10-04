# Configuration Reference

## Configuration principles

Configuration is environment-specific and secrets are never committed.

### Core variables

| Variable | Required | Purpose |
|---|---|---|
| DATABASE_URL | yes | runtime PostgreSQL connection |
| MIGRATION_DATABASE_URL | migration path | privileged migration connection |
| JWT_SECRET | yes | authentication signing/verification material |
| CREDENTIAL_ENCRYPTION_KEY | yes | encryption of persisted credentials |
| REDIS_URL | when Redis used | transient/cache/queue connection |
| POSTGRES_PASSWORD | deployment | database bootstrap |
| POSTGRES_RUNTIME_PASSWORD | deployment | least-privileged runtime role |
| N8N_DB_PASSWORD | when n8n used | n8n database credential |
| N8N_ENCRYPTION_KEY | when n8n used | n8n credential encryption |
| LISTMONK_DB_PASSWORD | when Listmonk used | Listmonk database credential |
| LISTMONK_ADMIN_PASSWORD | when Listmonk used | initial/admin credential |

## Requirements

Production values MUST be unique, high entropy and stored outside Git. Test values may be synthetic but must never be reused in production.

## Rotation

Rotate credentials using a controlled maintenance procedure. Where possible, support overlap during rotation to avoid unnecessary downtime. After rotation, verify authentication and revoke the previous credential.