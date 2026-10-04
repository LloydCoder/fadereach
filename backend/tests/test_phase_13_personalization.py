from personalization import validate_claim
def test_claim_requires_evidence(): assert not validate_claim("unsupported",[],.9)["allowed"]
def test_claim_accepts_evidence(): assert validate_claim("migration", [1], .8)["allowed"]
