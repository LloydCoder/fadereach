# Audit Logging

## Purpose

Audit logs provide attributable evidence of security- and governance-relevant actions. They are not a replacement for application logs or metrics.

## Minimum event fields

- event ID
- timestamp
- tenant ID where applicable
- actor type and actor ID
- action
- resource type/ID
- outcome
- request/correlation ID
- source/channel
- policy/approval reference where applicable
- safe metadata

## Must-audit actions

- authentication/security changes
- role/permission changes
- tenant changes
- credential/provider changes
- campaign creation/approval/start/pause/stop
- suppression changes
- administrative exports/deletions
- autonomous actions
- policy changes
- integration configuration
- incident response actions

## Integrity

Audit records should be append-oriented and access-controlled. Destructive mutation of audit history must be prohibited except through a documented retention mechanism.

## Privacy

Audit logs MUST minimize personal/message content. Secrets, tokens and full provider credentials are never logged. Retention is governed by Data Governance and applicable customer/legal requirements.