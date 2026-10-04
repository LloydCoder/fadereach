from deliverability_control import pre_send_decision
def test_policy_blocks(): assert pre_send_decision(1,1,0,False)["allowed"] is False
def test_healthy_sender_allows(): assert pre_send_decision(1,1,0,True)["allowed"] is True
