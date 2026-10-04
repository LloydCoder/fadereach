# Final Forensic Audit Checklist

## Repository
- README reconciled
- docs index reconciled
- no stale architecture claims
- no undocumented production dependency

## Security
- threat model current
- tenant isolation tested
- secrets excluded
- webhook authentication tested
- AI authority boundaries explicit

## Operations
- deployment tested
- rollback understood
- backups verified
- restore tested
- health/metrics/alerts defined

## Compliance
- data categories documented
- retention/deletion defined
- suppression controls documented
- jurisdictional constraints documented
- legal claims reviewed

## Product
- product boundary clear
- intelligence semantics clear
- campaign lifecycle clear
- autonomy levels clear

## CI
- exact promoted commit has green required workflows
- migration chain passes
- security tests pass
- frontend build passes
- Compose validation passes
- shell validation passes

A final audit must distinguish repository evidence from external production evidence.