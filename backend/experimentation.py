def validate_experiment(primary_metric:str,minimum_sample_size:int,guardrails:dict)->dict:
 valid=bool(primary_metric and minimum_sample_size>=30)
 return {"valid":valid,"primary_metric":primary_metric,"minimum_sample_size":minimum_sample_size,"guardrails":guardrails}
