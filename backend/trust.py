def build_trust_export(controls:dict,data_handling:dict,ai_governance:dict,availability:dict,subprocessors:list,compliance:dict)->dict:
 return {"export_version":"trust.v1","controls":controls,"data_handling":data_handling,"ai_governance":ai_governance,"availability":availability,"subprocessors":subprocessors,"compliance_mappings":compliance}
