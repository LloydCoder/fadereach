from dynamic_autonomy import decide_autonomy
def test_low_risk_allows(): assert decide_autonomy(.1,.9,.1,0)["decision"]=="allow"
def test_high_risk_escalates(): assert decide_autonomy(.95,.9,.1,0)["decision"]=="escalate"
def test_reputation_escalates(): assert decide_autonomy(.2,.9,.9,0)["decision"]=="escalate"
