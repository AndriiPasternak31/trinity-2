"""
Watchdog Integration Tests (test_watchdog.py)

Tests for Issue #129: Active watchdog remediation of stuck executions.
Integration tests against the running backend — verify cleanup report
includes watchdog fields.

Feature Flow: docs/memory/feature-flows/cleanup-service.md
"""

import pytest
from utils.api_client import TrinityApiClient
from utils.assertions import (
    assert_status,
    assert_json_response,
)


class TestWatchdogCleanupReportFields:
    """Tests that cleanup report includes Issue #129 watchdog fields."""

    pytestmark = pytest.mark.smoke

    def test_cleanup_status_includes_watchdog_fields(self, api_client: TrinityApiClient):
        """GET /api/monitoring/cleanup-status report includes watchdog fields."""
        response = api_client.get("/api/monitoring/cleanup-status")
        assert_status(response, 200)
        data = response.json()

        if data.get("last_report"):
            report = data["last_report"]
            assert "orphaned_executions" in report, "Missing orphaned_executions field"
            assert "auto_terminated" in report, "Missing auto_terminated field"
            assert isinstance(report["orphaned_executions"], int)
            assert isinstance(report["auto_terminated"], int)

    def test_cleanup_trigger_includes_watchdog_fields(self, api_client: TrinityApiClient):
        """POST /api/monitoring/cleanup-trigger report includes watchdog fields."""
        response = api_client.post("/api/monitoring/cleanup-trigger")
        assert_status(response, 200)
        data = assert_json_response(response)

        report = data["report"]
        assert "orphaned_executions" in report, "Missing orphaned_executions field"
        assert "auto_terminated" in report, "Missing auto_terminated field"
        assert isinstance(report["orphaned_executions"], int)
        assert isinstance(report["auto_terminated"], int)
        assert report["orphaned_executions"] >= 0
        assert report["auto_terminated"] >= 0

    def test_cleanup_total_includes_watchdog_fields(self, api_client: TrinityApiClient):
        """Cleanup total correctly sums all fields including watchdog additions."""
        response = api_client.post("/api/monitoring/cleanup-trigger")
        assert_status(response, 200)
        report = response.json()["report"]

        expected_total = (
            report["orphaned_executions"]
            + report["auto_terminated"]
            + report["stale_executions"]
            + report["no_session_executions"]
            + report["orphaned_skipped"]
            + report["stale_activities"]
            + report["stale_slots"]
        )
        assert report["total"] == expected_total

    def test_cleanup_trigger_requires_auth(self, unauthenticated_client: TrinityApiClient):
        """Watchdog cleanup trigger requires authentication."""
        response = unauthenticated_client.post("/api/monitoring/cleanup-trigger")
        assert response.status_code in [401, 403]
