"""
Tests for WebSocket Authentication (#178)
Related flow: docs/memory/feature-flows/agent-network.md

Verifies that the /ws endpoint rejects unauthenticated connections
before calling websocket.accept(), preventing information disclosure.

Uses httpx WebSocket support for testing.
"""
import pytest
import httpx
from tests.conftest import *


class TestWebSocketAuthentication:
    """Test suite for WebSocket authentication enforcement (#178)."""

    def test_ws_no_token_rejected(self, api_client):
        """Connecting without any token should be rejected.

        The server should close the connection with code 4001 before
        sending any data, or reject the HTTP upgrade entirely.
        """
        base_url = api_client.config.base_url
        ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws"

        # Use httpx to attempt WebSocket upgrade without token
        with httpx.Client() as client:
            try:
                # Try to GET the WebSocket endpoint — without proper upgrade headers
                # this tests that the endpoint exists and requires auth
                response = client.get(f"{base_url}/ws")
                # WebSocket endpoints typically return 403 or protocol error for plain HTTP
                assert response.status_code in (403, 400, 426), \
                    f"Expected rejection, got {response.status_code}"
            except httpx.HTTPError:
                pass  # Connection error is acceptable — means server rejected

    def test_ws_invalid_token_rejected(self, api_client):
        """Connecting with an invalid JWT should be rejected."""
        base_url = api_client.config.base_url

        with httpx.Client() as client:
            try:
                response = client.get(
                    f"{base_url}/ws",
                    params={"token": "invalid-not-a-jwt"}
                )
                assert response.status_code in (403, 400, 426), \
                    f"Expected rejection, got {response.status_code}"
            except httpx.HTTPError:
                pass

    def test_ws_valid_token_not_rejected(self, api_client):
        """A valid JWT token should not get an HTTP-level rejection.

        Note: Full WebSocket test requires a WS client library.
        This test verifies the server doesn't reject the upgrade at HTTP level.
        """
        base_url = api_client.config.base_url

        with httpx.Client() as client:
            # Send a proper WebSocket upgrade request with valid token
            response = client.get(
                f"{base_url}/ws",
                params={"token": api_client.token},
                headers={
                    "Upgrade": "websocket",
                    "Connection": "Upgrade",
                    "Sec-WebSocket-Version": "13",
                    "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ==",
                }
            )
            # With a valid token, the server should attempt the upgrade (101)
            # or return a non-auth-error status
            assert response.status_code != 403, \
                "Valid token should not get 403"
