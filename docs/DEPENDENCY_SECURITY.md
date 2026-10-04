# Dependency Security

Dependency security is part of the software supply-chain boundary.

## Requirements
- review dependency changes
- prefer maintained releases
- avoid unnecessary dependencies
- monitor known vulnerabilities
- pin/lock where appropriate
- verify container base images
- keep GitHub Action references immutable where practical
- avoid unnecessary CI write permissions

Scanner findings must be triaged by exploitability, reachability, exposure and remediation availability; blindly upgrading can introduce incompatible changes.