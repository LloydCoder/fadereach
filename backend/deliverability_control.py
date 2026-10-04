def pre_send_decision(sender_health:float,domain_health:float,recipient_risk:float,policy_ok:bool)->dict:
 risk=max(0,min(1,.35*(1-sender_health)+.3*(1-domain_health)+.35*recipient_risk))
 allowed=policy_ok and risk<.7
 return {"allowed":allowed,"decision_code":"ALLOW" if allowed else ("POLICY_BLOCK" if not policy_ok else "REPUTATION_RISK"),"policy_version":"deliverability.v1","risk_score":risk}
