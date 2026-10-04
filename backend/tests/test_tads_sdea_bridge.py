import hashlib
import hmac
import json
import time

from routers.integrations import _verify


def test_signal_signature_contract(monkeypatch):
    monkeypatch.setenv("SIGNAL_INGEST_SECRET", "x" * 64)
    import routers.integrations as integrations
    integrations.SIGNAL_SECRET = "x" * 64

    body = json.dumps({"external_id": "evt-1"}).encode()
    ts = str(int(time.time()))
    sig = hmac.new(
        integrations.SIGNAL_SECRET.encode(),
        f"{ts}.".encode() + body,
        hashlib.sha256,
    ).hexdigest()
    _verify(body, f"sha256={sig}", ts)
