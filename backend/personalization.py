"""Deterministic gate for evidence-backed personalization."""
def validate_claim(claim:str,evidence_refs:list,confidence:float)->dict:
 return {"allowed":bool(claim.strip() and evidence_refs and 0<=confidence<=1),"claim":claim,"evidence_refs":evidence_refs,"confidence":confidence}
