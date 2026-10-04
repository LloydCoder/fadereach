# Production Deployment

## Supported model

FadeReach currently supports a simple single-host Docker Compose production topology. This is deliberately conservative until measured scale justifies distributed infrastructure.

## Preconditions

- supported Ubuntu host
- SSH access
- DNS control
- TLS/edge configuration
- Docker/Compose
- production environment secrets
- backups configured
- CI green on the commit being promoted
- worker service included in the Compose topology

## Bootstrap

From a checked-out repository, the canonical bootstrap is:

```bash
sudo bash infrastructure/setup.sh
```

Review the script before execution on a new host. It must not be treated as evidence that production is healthy.

## Promotion

1. Confirm target commit is the intended main commit.
2. Confirm CI green.
3. Confirm environment variables/secrets.
4. Confirm database backup/recovery posture.
5. Apply migrations.
6. Build/pull application images.
7. Start services.
8. Verify Compose state.
9. Verify API health.
10. Verify critical smoke paths.
11. Verify logs and resource health.
12. Record deployment commit.

The manual production workflow is intentionally explicit and must not silently deploy arbitrary pushes.

## Rollback

Rollback is a controlled operation. Revert application code to a known-good commit only when database compatibility is understood. Never blindly downgrade a database migration in production.

## Post-deploy

Verify authentication, tenant isolation, campaign state, provider connectivity, webhook processing, suppression enforcement and health endpoints. Record evidence in the deployment/incident record.

## Process separation

The API image never mutates the database schema during application startup and never starts durable workers. Production promotion applies Alembic explicitly before `docker compose up`. The `worker` service runs outbound execution and retention enforcement independently so increasing API replicas cannot multiply background workers.
