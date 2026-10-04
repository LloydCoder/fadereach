from routers.intelligence import _buyer_hypothesis, _signal_key


def test_intelligence_hypothesis_is_deterministic():
    assert _buyer_hypothesis("CTO", "Example") == "CTO"
    assert _signal_key("reconos_funding_round") == "funding"
    assert _signal_key("unknown_signal") == ""
