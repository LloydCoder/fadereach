"""Governed AI decision gate: AI proposes; deterministic policy decides."""
def evaluate_ai_decision(risk_score:float,evidence_refs:list,requires_approval:bool)->dict:
 risk=max(0,min(1,float(risk_score)))
 if not evidence_refs: return {"decision":"deny","reason":"missing_evidence"}
 if risk>=.8: return {"decision":"deny","reason":"high_risk"}
 if requires_approval or risk>=.5: return {"decision":"review","reason":"approval_required"}
 return {"decision":"allow","reason":"policy_pass"}
