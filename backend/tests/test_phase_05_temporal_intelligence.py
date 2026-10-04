from datetime import datetime, timedelta, timezone
from temporal_intelligence import compute_trajectory

def test_acceleration_and_persistence_states():
    now = datetime.now(timezone.utc)
    points = [
        {"observed_at": now - timedelta(days=20), "strength": 20},
        {"observed_at": now - timedelta(days=10), "strength": 40},
        {"observed_at": now, "strength": 70},
    ]
    result = compute_trajectory(points)
    assert result["state"] == "accelerating"
    assert result["observation_count"] == 3

def test_reversal_is_explicit():
    now = datetime.now(timezone.utc)
    points = [
        {"observed_at": now - timedelta(days=30), "strength": 70},
        {"observed_at": now - timedelta(days=20), "strength": 90},
        {"observed_at": now - timedelta(days=10), "strength": 60},
        {"observed_at": now, "strength": 40},
    ]
    assert compute_trajectory(points)["state"] == "reversing"

def test_old_signal_decays():
    old = datetime.now(timezone.utc) - timedelta(days=180)
    result = compute_trajectory([{"observed_at": old, "strength": 80}])
    assert result["state"] == "decayed"
