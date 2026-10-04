"""Application-layer security controls.

These controls are deliberately small and deterministic. They complement the
edge proxy and database/RLS controls rather than replacing them.
"""

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


DEFAULT_ALLOWED_HOSTS = (
    "fadereach.app,fadereach.tinlance.com,localhost,127.0.0.1"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply baseline browser/API security headers and request-size limits."""

    async def dispatch(self, request: Request, call_next):
        max_body = int(os.getenv("MAX_REQUEST_BODY_BYTES", str(2 * 1024 * 1024)))
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > max_body:
                    return Response("Request body too large", status_code=413)
            except ValueError:
                return Response("Invalid Content-Length", status_code=400)

        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; "
            "object-src 'none'",
        )
        if request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response


def allowed_hosts() -> list[str]:
    raw = os.getenv("ALLOWED_HOSTS", DEFAULT_ALLOWED_HOSTS)
    return [host.strip() for host in raw.split(",") if host.strip()]
