# Software Supply-Chain Evidence

FadeReach treats dependency inventory and provenance as release evidence rather than an informal checklist.

## CI controls

The required CI workflow performs:

- Python dependency vulnerability auditing with pip-audit.
- Bandit static analysis.
- CycloneDX SBOM generation from the authoritative backend requirements file.
- SBOM structural validation.
- SBOM retention as a GitHub Actions artifact for 90 days.
- Docker Compose image builds for the API, dedicated worker and frontend.

## Scope and limits

The current CI SBOM is a Python application dependency SBOM. It does not by itself constitute a complete container, operating-system, runtime, or transitive frontend SBOM. Container and frontend supply-chain assurance remain separate hardening work.

## Release principle

Production releases must retain the exact source commit, CI run and generated SBOM evidence associated with the promoted artifact. SLSA provenance is the target model for stronger artifact-to-source traceability.

## References

- CycloneDX SBOM specification: https://cyclonedx.org/specification/overview/
- SLSA specification and provenance: https://slsa.dev/spec/v1.2/