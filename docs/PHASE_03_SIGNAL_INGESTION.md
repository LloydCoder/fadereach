# Phase 3 — Signal Ingestion & Normalization

Phase 3 establishes governed ingestion metadata and a canonical normalized signal contract. Raw source identity remains preserved while normalized type/category, observation time, source URL, freshness, payload fingerprint, schema version and normalization status become first-class fields.

Supported source classes include TADS, SDEA, ReconOS and approved internal/public source adapters. Job postings remain one signal class rather than the system's definition of intent. Source trust is explicitly tiered and ingestion runs are measurable.

## Phase gate

Source governance, ingestion-run accounting, normalized fields, deduplication/fingerprinting, tenant RLS, endpoint normalization behavior, tests, documentation and all CI workflows must be green before Phase 4 starts.
