from fastapi.testclient import TestClient

from main import app


def test_health_route_is_registered():
    routes = {route.path for route in app.routes}
    assert "/api/health" in routes


def test_core_router_surface_is_registered():
    routes = {route.path for route in app.routes}
    expected = {
        "/api/auth/login",
        "/api/campaigns",
        "/api/leads",
        "/api/domains",
        "/api/inbox",
        "/api/analytics",
        "/api/tenants",
        "/api/rbac",
        "/api/webhooks",
        "/api/public",
    }
    missing = expected - routes
    assert not missing, f"Missing routes: {sorted(missing)}"


def test_app_imports_without_starting_external_services():
    client = TestClient(app)
    assert client is not None


def test_expected_core_routes_are_unique():
    routes = [route.path for route in app.routes]
    assert len(routes) == len(set(routes))
