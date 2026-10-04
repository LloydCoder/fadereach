# Incident Response

## Severity

- SEV-1: active security breach, unauthorized outbound activity, major data exposure or material service failure.
- SEV-2: significant tenant/service impact with containment available.
- SEV-3: limited degradation or isolated defect.
- SEV-4: minor issue/request.

## Response lifecycle

Detect → Triage → Contain → Preserve evidence → Eradicate → Recover → Validate → Communicate → Postmortem.

## Immediate controls

For suspected unauthorized outbound activity, pause the affected campaign/provider before debugging secondary symptoms. For suspected credential compromise, revoke/rotate the credential. For suspected tenant isolation failure, disable affected access path and preserve evidence.

## Evidence

Preserve deployment commit, relevant audit IDs, request IDs, timestamps, safe logs, provider event IDs and configuration changes. Do not copy secrets into incident records.

## Post-incident

Document root cause, contributing factors, customer impact, timeline, controls that failed, corrective actions, verification evidence and documentation updates.