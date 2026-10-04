# TADS/SDEA Integration

TADS supplies account and demand-signal intelligence; SDEA operationalizes signal-driven engineering acquisition. FadeReach consumes validated signals/evidence for outbound reasoning and execution.

Signals should include stable identifiers, observed timestamps, source/provenance references, account identity, signal type, evidence references and quality metadata.

FadeReach must preserve upstream provenance and must not silently rewrite an upstream fact into a new fact.

Repeated upstream events must not create duplicate campaigns, opportunities or outbound actions.

Missing/invalid tenant mapping, malformed signal, missing provenance or incompatible schema version fails closed for execution while allowing safe diagnostics.