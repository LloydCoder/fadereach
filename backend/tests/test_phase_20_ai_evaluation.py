from ai_evaluation import evaluate_release
def test_clean_suite_releases(): assert evaluate_release([{"passed":True,"severity":"info"}])["release_allowed"]
def test_failed_suite_blocks(): assert not evaluate_release([{"passed":False,"severity":"high"}])["release_allowed"]
def test_critical_blocks(): assert not evaluate_release([{"passed":False,"severity":"critical"}])["release_allowed"]
