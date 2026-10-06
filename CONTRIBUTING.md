# Contributing to FadeReach

Thank you for improving FadeReach.

FadeReach is proprietary source-available software owned by Tinlance Limited. A public repository does not grant rights to redistribute, commercialize, host, or create competing services. See [LICENSE](LICENSE) and [docs/LICENSING.md](docs/LICENSING.md).

## Before you start

Read:

- [README.md](README.md)
- [docs/README.md](docs/README.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/SECURITY.md](docs/SECURITY.md)
- [SECURITY.md](SECURITY.md)

Behavioral changes must reconcile implementation, tests, security controls, operational assumptions, and documentation in the same change.

## Contribution flow

1. Fork the repository if you are working outside the Tinlance-maintained repository.
2. Create a focused branch from `main`, for example `fix/webhook-idempotency`.
3. Make the smallest coherent change.
4. Add or update automated tests for behavior changes.
5. Update documentation and migration notes when applicable.
6. Run the relevant local checks.
7. Open a pull request against `main`.

Do not commit directly to `main` unless repository governance explicitly permits it.

## Engineering requirements

- Preserve server-side authorization and tenant isolation.
- Do not introduce a second authority for governed agent execution, secrets, policy, sandboxing, or audit.
- Keep database schema changes in Alembic migrations.
- Treat webhook payloads, email content, URLs, retrieved content, and model output as untrusted.
- Keep secrets out of source control and logs.
- Fail closed for authorization, tenant resolution, secret validation, suppression, and high-risk outbound actions.
- Do not claim production readiness without reproducible evidence.

## Testing

The canonical repository gate is the GitHub Actions CI workflow. Locally, the most useful checks are:

```bash
cd backend
python -m compileall -q .
pip install -r requirements.txt
PYTHONPATH=. pytest -q tests
cd ..
docker compose config
cd frontend
npm install --no-audit --no-fund
npm run build
```

Use the supported Python baseline documented in the README and CI workflow.

## Commits and pull requests

Use concise, imperative Conventional Commit-style subjects where practical, such as:

- `feat: add provider capability registry`
- `fix: reject replayed webhook events`
- `docs: reconcile deployment guidance`
- `test: cover tenant isolation`

A pull request should explain:

- problem and user impact;
- implementation and design choice;
- tests executed;
- security and tenancy impact;
- migration impact;
- operational/rollback impact;
- documentation updated.

## Security-sensitive changes

Never publish exploit details or credentials in an issue or pull request. Follow [SECURITY.md](SECURITY.md) for vulnerability reports.

## Review standard

A change is ready to merge when:

- required CI checks are green on the proposed commit;
- tests cover the changed behavior;
- security and tenant boundaries remain intact;
- documentation is consistent with implementation;
- migrations are reversible or operationally documented where appropriate;
- the pull request is small enough to review confidently.

Maintainers may request additional evidence for changes affecting authorization, outbound execution, provider integrations, data retention, billing, AI autonomy, or production deployment.
