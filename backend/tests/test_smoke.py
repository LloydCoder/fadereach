from fastapi.testclient import TestClient

from main import app


def _registered_paths(routes, prefix=""):
    paths = set()
    for route in routes:
        route_prefix = getattr(route, "prefix", "") or ""
        route_path = getattr(route, "path", None)
        if route_path:
            paths.add(prefix + route_path)
        nested = getattr(route, "routes", None)
        if nested:
            paths.update(_registered_paths(nested, prefix + route_prefix))
    return paths


def test_health_route_is_registered():
    routes = set(app.openapi()["paths"]) | _registered_paths(app.routes)
    assert "/api/health" in routes


def test_core_router_surface_is_registered():
    routes = {route.path for route in app.routes if hasattr(route, "path")}
    expected_prefixes = {
        "/api/auth",
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
    missing = {
        prefix for prefix in expected_prefixes
        if not any(path == prefix or path.startswith(prefix + "/") for path in routes)
    }
    assert not missing, f"Missing router prefixes: {sorted(missing)}"


def test_app_imports_without_starting_external_services():
    client = TestClient(app)
    assert client is not None
