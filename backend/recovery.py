def recovery_gate(status:str,rto:int,rpo:int,target_rto:int,target_rpo:int)->dict:
 return {"passed":status=="passed" and rto<=target_rto and rpo<=target_rpo,"status":status,"rto_seconds":rto,"rpo_seconds":rpo}
