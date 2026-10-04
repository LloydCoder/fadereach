# Phase 6 — Account Intelligence Graph

Phase 6 establishes a durable account graph connecting accounts to people, technologies, initiatives, signals, evidence, opportunities, campaigns and outcomes. Edges are typed, tenant-scoped, confidence-bearing, temporally bounded and optionally evidence-linked.

The graph is a commercial intelligence projection, not a replacement for PostgreSQL relational truth. Traversals must remain tenant-scoped and claims should retain evidence references. Entity resolution continues through canonical domains and source aliases.

## Phase gate

Graph schema, typed edges, evidence linkage, temporal validity, tenant isolation, traversal API, tests, documentation and all CI workflows must be green before Phase 7 starts.
