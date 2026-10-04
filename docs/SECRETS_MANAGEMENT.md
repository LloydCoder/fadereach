# Secrets Management

## Scope

Secrets include JWT/signing keys, database passwords, credential-encryption keys, provider credentials, n8n encryption material and deployment SSH credentials.

## Rules

1. Never commit secrets.
2. Never print secrets in CI logs.
3. Never return secrets from APIs.
4. Encrypt persisted provider credentials.
5. Use least-privileged credentials.
6. Separate development/test/production secrets.
7. Rotate credentials after suspected exposure.
8. Record rotation events without recording secret values.

## Lifecycle

Generate → store securely → inject at runtime → use minimally → monitor → rotate → revoke → destroy.

## Production

The current deployment uses environment/host secret configuration. A production secret manager may be introduced when scale or compliance requires it, but the application contract remains: secret material is not source-controlled and is unavailable to untrusted processes.

## Compromise response

Immediately disable/revoke the affected credential, preserve relevant audit evidence, determine blast radius, replace the secret, validate dependent services and document the incident. If a signing/encryption key is compromised, follow the corresponding key-rotation and data-recovery procedure; do not simply overwrite the environment variable and declare recovery complete.