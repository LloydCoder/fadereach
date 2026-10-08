#!/usr/bin/env python3
"""Fail-closed FadeReach verification against the canonical TSIC adapter."""
from __future__ import annotations
import json
from urllib.request import Request, urlopen

TSIC_REVISION = "72c3664d7917bf9f8adb071713719589ff159972"
RAW_ROOT = f"https://raw.githubusercontent.com/LloydCoder/tinlance-system-integration/{TSIC_REVISION}"
REQUIRED = {"identity-context","event-envelope","delivery-semantics","trace-context","economic-attribution"}

def fetch_json(path: str) -> dict:
    request = Request(f"{RAW_ROOT}/{path}", headers={"Accept":"application/json","User-Agent":"tinlance-fadereach-ci"})
    with urlopen(request, timeout=15) as response:
        if response.status != 200: raise RuntimeError(f"TSIC contract fetch failed for {path}: HTTP {response.status}")
        return json.load(response)

def main() -> None:
    manifest = fetch_json("manifests/ecosystem.json")
    adapter = fetch_json("integrations/fadereach/adapter.json")
    registry = fetch_json("catalog/contracts/registry.json")
    system = next(x for x in manifest["systems"] if x["id"] == "fadereach")
    assert system["repository"] == "LloydCoder/fadereach"
    assert system["governance_role"] == "outreach_execution_authority"
    assert adapter["source_system"] == "tsic" and adapter["target_system"] == "fadereach"
    assert adapter["status"] == "reference-contract"
    assert {x["tsic_contract"] for x in adapter["contract_bindings"]} == REQUIRED
    assert {x["id"] for x in registry["contracts"]} >= REQUIRED
    assert adapter["authority"]["integration_contracts"] == "tsic"
    assert adapter["authority"]["outreach_execution"] == "fadereach"
    assert adapter["authority"]["execution_authority"] == "agent-platform"
    required = {"outreach_is_tenant_scoped","suppression_and_consent_controls_are_preserved","duplicate_actions_are_idempotent","provider_failures_are_recoverable","outreach_does_not_grant_policy_or_runtime_authority","tsic_remains_integration_authority","agent-platform_remains_execution_authority"}
    assert set(adapter["invariants"]) == required
    print(f"PASS FadeReach TSIC conformance: revision={TSIC_REVISION} contracts={len(REQUIRED)}")

if __name__ == "__main__":
    main()
