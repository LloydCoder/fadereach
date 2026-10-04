from trust import build_trust_export
def test_trust_export_has_required_sections(): assert set(build_trust_export({}, {}, {}, {}, [], {}).keys())=={"export_version","controls","data_handling","ai_governance","availability","subprocessors","compliance_mappings"}
