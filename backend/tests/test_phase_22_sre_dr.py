from recovery import recovery_gate
def test_recovery_passes_targets(): assert recovery_gate("passed",60,30,120,60)["passed"]
def test_recovery_fails_exceeded_target(): assert not recovery_gate("passed",180,30,120,60)["passed"]
