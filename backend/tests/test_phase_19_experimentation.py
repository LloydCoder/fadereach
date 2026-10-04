from experimentation import validate_experiment
def test_experiment_requires_metric(): assert not validate_experiment("",100,{})["valid"]
def test_experiment_minimum_sample(): assert validate_experiment("qualified_reply",100,{"max_bounce":.03})["valid"]
