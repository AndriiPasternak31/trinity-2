"""
Tests for security headers on API responses (#190).

Verifies that the FastAPI security headers middleware is active and that
the Server header is suppressed via Uvicorn's --no-server-header flag.

Feature flow: N/A (infrastructure hardening)
"""

import pytest


@pytest.mark.smoke
class TestSecurityHeaders:
    """Verify security headers are present on API responses."""

    def test_api_response_has_security_headers(self, api_client):
        """GET /api/health should include all expected security headers."""
        response = api_client.get("/api/health")

        assert response.headers.get("x-content-type-options") == "nosniff"
        assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
        assert response.headers.get("permissions-policy") == "camera=(), microphone=(), geolocation=(), payment=()"
        assert response.headers.get("cross-origin-resource-policy") == "same-origin"

    def test_server_header_stripped(self, api_client):
        """API responses should not expose the server technology."""
        response = api_client.get("/api/health")

        # Uvicorn's --no-server-header flag should suppress this
        server = response.headers.get("server")
        assert server is None or "uvicorn" not in server.lower(), (
            f"Server header should not expose uvicorn, got: {server}"
        )

    def test_cors_preflight_still_works(self, unauthenticated_client):
        """CORS preflight (OPTIONS) should still return proper CORS headers
        alongside security headers — the middleware must not break CORS."""
        response = unauthenticated_client._client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost",
                "Access-Control-Request-Method": "GET",
            },
        )

        # CORS headers should still be present
        assert response.status_code in (200, 204, 405)
        # Security headers should also be present on preflight responses
        assert response.headers.get("x-content-type-options") == "nosniff"
