REQUIRED_GATES={"code","security","integration","performance","ai","dr","supply_chain","compliance","production_workload","pilot_customer","production_customer","independent_validation"}
def evaluate_ga(gates:dict)->dict:
 missing=sorted(k for k in REQUIRED_GATES if gates.get(k)!="satisfied")
 return {"enterprise_ga":not missing,"missing":missing,"required_gates":sorted(REQUIRED_GATES)}
