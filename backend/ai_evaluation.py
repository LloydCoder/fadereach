SCENARIOS=("AI-001" "AI-002" "AI-003" "AI-004" "AI-005" "AI-006" "AI-007" "AI-008" "AI-009" "AI-010" "AI-011" "AI-012" "AI-013" "AI-014" "AI-015")
def evaluate_release(results:list[dict])->dict:
 critical=[r for r in results if r.get("severity")=="critical" and not r.get("passed")]
 failed=[r for r in results if not r.get("passed")]
 return {"release_allowed":not critical and not failed,"failed":len(failed),"critical":len(critical)}
