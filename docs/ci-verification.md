# CI verification

FadeReach CI is the merge gate for the production-hardening sequence.

## Required checks

The FadeReach CI workflow must complete successfully for the commit under review:

- backend Python compilation/import
- Alembic upgrade from an empty PostgreSQL database
- tenant RLS enforcement using the non-owner runtime role
- backend smoke tests
- frontend production build
- Docker Compose configuration and image builds
- shell-script syntax validation

## Interpretation

A green CI run proves that the repository's declared automated checks passed. It does not by itself prove external DNS, email-provider reputation, third-party credentials, production secrets, VPS state, backups, disaster recovery, or legal compliance.

Production promotion therefore requires the deployment checklist in the README in addition to green CI.

## Manual workflow

The workflow also supports workflow_dispatch for deliberate verification of the default branch. It must never be treated as a substitute for the push/pull-request gate.
