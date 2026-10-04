import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from middleware.security import SecurityHeadersMiddleware, allowed_hosts
from routers.auth import LoginReq, SignupReq
from routers.webhooks import _mapped_plan, _parse_webhook_json, _require_event_id, MAX_WEBHOOK_BODY_BYTES


def test_security_middleware_rejects_oversized_request(monkeypatch):
    monkeypatch.setenv("MAX_REQUEST_BODY_BYTES", "4")
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.post("/")
    async def root():
        return {"ok": True}

    with TestClient(app) as client:
        response = client.post("/", content=b"12345")
    assert response.status_code == 413


def test_security_headers_are_present():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/")
    async def root():
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"


def test_auth_password_bounds():
    with pytest.raises(ValueError):
        LoginReq(email="user@example.test", password="x" * 73)
    with pytest.raises(ValueError):
        SignupReq(email="user@example.test", name="User", password="x" * 73)


def test_webhook_payload_and_event_validation():
    with pytest.raises(Exception):
        _parse_webhook_json(b"not-json")
    with pytest.raises(Exception):
        _parse_webhook_json(b"[]")
    with pytest.raises(Exception):
        _require_event_id("")
    assert _require_event_id("subscription.created:123") == "subscription.created:123"


def test_allowed_hosts_has_production_defaults():
    hosts = allowed_hosts()
    assert "fadereach.app" in hosts
    assert "fadereach.tinlance.com" in hosts


def test_webhook_body_limit_is_bounded():
    with pytest.raises(Exception):
        _parse_webhook_json(b"{" + b'"x":"' + b"a" * MAX_WEBHOOK_BODY_BYTES + b'"}')


def test_billing_plan_mapping_fails_closed():
    assert _mapped_plan({"variant-1": "growth"}, "variant-1", "test") == "growth"
    with pytest.raises(Exception):
        _mapped_plan({"variant-1": "growth"}, "unknown", "test")
    with pytest.raises(Exception):
        _mapped_plan({"": "growth"}, "", "test")
