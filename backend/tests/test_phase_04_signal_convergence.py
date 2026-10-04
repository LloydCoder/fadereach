from datetime import datetime, timedelta, timezone
from signal_convergence import compute_convergence

def test_independent_sources_raise_convergence():
    now = datetime.now(timezone.utc)
    result = compute_convergence([
        {"id": 1, "source": "tads", "trust_tier": "T1", "strength": 80, "polarity": 1, "observed_at": now},
        {"id": 2, "source": "sdea", "trust_tier": "T1", "strength": 70, "polarity": 1, "observed_at": now},
        {"id": 3, "source": "reconos", "trust_tier": "T2", "strength": 60, "polarity": 1, "observed_at": now},
    ])
    assert result["independent_source_count"] == 3
    assert result["convergence_score"] > 0
    assert result["state"] == "active"

def test_contradiction_reduces_convergence():
    now = datetime.now(timezone.utc)
    positive = compute_convergence([
        {"source": "tads", "trust_tier": "T1", "strength": 80, "polarity": 1, "observed_at": now},
        {"source": "sdea", "trust_tier": "T1", "strength": 70, "polarity": 1, "observed_at": now},
    ])
    mixed = compute_convergence([
        {"source": "tads", "trust_tier": "T1", "strength": 80, "polarity": 1, "observed_at": now},
        {"source": "sdea", "trust_tier": "T1", "strength": 70, "polarity": 1, "observed_at": now},
        {"source": "reconos", "trust_tier": "T2", "strength": 90, "polarity": -1, "observed_at": now},
    ])
    assert mixed["convergence_score"] < positive["convergence_score"]
    assert mixed["contradiction_count"] == 1

def test_stale_signals_decay():
    old = datetime.now(timezone.utc) - timedelta(days=180)
    fresh = datetime.now(timezone.utc)
    stale = compute_convergence([{"source": "tads", "trust_tier": "T1", "strength": 80, "observed_at": old}])
    current = compute_convergence([{"source": "tads", "trust_tier": "T1", "strength": 80, "observed_at": fresh}])
    assert stale["convergence_score"] < current["convergence_score"]
