def decide_autonomy(risk:float,evidence_confidence:float,reputation_risk:float,financial_exposure:float)->dict:
 r=max(0,min(1,risk)); e=max(0,min(1,evidence_confidence)); rep=max(0,min(1,reputation_risk))
 if rep>=.8 or r>=.9: d="escalate"
 elif r>=.7 or e<.5: d="block"
 elif r>=.4: d="review"
 else: d="allow"
 return {"decision":d,"policy_version":"autonomy.v1","risk_score":r,"evidence_confidence":e,"reputation_risk":rep,"financial_exposure":max(0,financial_exposure)}
