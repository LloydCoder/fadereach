from routers.autopilot import _plan_hash, _hash_matches


def test_autopilot_plan_hash_is_stable():
    plan = {"goal": "test", "policy_snapshot": {"max_accounts": 10}}
    digest = _plan_hash(plan)
    assert _hash_matches(digest, _plan_hash(plan))
    assert not _hash_matches(digest, _plan_hash({**plan, "goal": "changed"}))
