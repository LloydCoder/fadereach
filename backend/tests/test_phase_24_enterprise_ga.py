from enterprise_ga import evaluate_ga
def test_ga_requires_external_proof(): assert "pilot_customer" in evaluate_ga({})["missing"] and "independent_validation" in evaluate_ga({})["missing"]
def test_ga_only_when_all_satisfied(): assert evaluate_ga({k:"satisfied" for k in evaluate_ga({})["required_gates"]})["enterprise_ga"]
