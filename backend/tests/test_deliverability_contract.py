import os

import pytest

from routers.domains import normalize_domain
from routers.unsubscribe import create_unsubscribe_token, _decode_token


def test_domain_normalization():
    assert normalize_domain("Example.COM.") == "example.com"
    with pytest.raises(Exception):
        normalize_domain("127.0.0.1")
    with pytest.raises(Exception):
        normalize_domain("not a domain")


def test_unsubscribe_token_is_signed_and_expiring(monkeypatch):
    monkeypatch.setenv("UNSUBSCRIBE_SECRET", "x" * 64)
    token = create_unsubscribe_token("tenant-a", "USER@Example.COM")
    payload = _decode_token(token)
    assert payload["tenant_id"] == "tenant-a"
    assert payload["email"] == "user@example.com"

    with pytest.raises(Exception):
        _decode_token(token + "tampered")
