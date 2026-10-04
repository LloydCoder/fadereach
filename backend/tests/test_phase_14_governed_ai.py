from governed_ai import evaluate_ai_decision
def test_ai_without_evidence_denied(): assert evaluate_ai_decision(.1,[],False)["decision"]=="deny"
def test_high_risk_denied(): assert evaluate_ai_decision(.9,[1],False)["decision"]=="deny"
def test_medium_risk_review(): assert evaluate_ai_decision(.6,[1],False)["decision"]=="review"
