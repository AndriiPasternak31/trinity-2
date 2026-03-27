"""
Unit tests for subscription BOLA fix (Issue #182).

Verifies that PUT /api/subscriptions/agents/{name} and
DELETE /api/subscriptions/agents/{name} use can_user_share_agent
(owner/admin only) instead of can_user_access_agent (any shared user).

Issue: https://github.com/abilityai/trinity/issues/182
Module: src/backend/routers/subscriptions.py
"""

import os
import sys
import pytest
import ast

# Path to the router source
ROUTER_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', 'src', 'backend', 'routers', 'subscriptions.py'
)


class TestSubscriptionBOLA:
    """Issue #182: subscription mutation endpoints must use owner-only auth."""

    @pytest.fixture(autouse=True)
    def _load_source(self):
        """Load the router source once."""
        with open(ROUTER_PATH) as f:
            self.source = f.read()
        self.tree = ast.parse(self.source)

    def _get_function_source(self, func_name: str) -> str:
        """Extract the source of a specific function from the AST."""
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == func_name:
                    return ast.get_source_segment(self.source, node)
        raise ValueError(f"Function {func_name} not found")

    # ---- PUT /api/subscriptions/agents/{name} ----

    def test_assign_uses_can_user_share_agent(self):
        """assign_subscription_to_agent must call can_user_share_agent, not can_user_access_agent."""
        src = self._get_function_source("assign_subscription_to_agent")
        assert "can_user_share_agent" in src, (
            "assign_subscription_to_agent must use can_user_share_agent (owner/admin only)"
        )
        assert "can_user_access_agent" not in src, (
            "assign_subscription_to_agent must NOT use can_user_access_agent (allows shared users)"
        )

    def test_assign_returns_403_message(self):
        """assign_subscription_to_agent 403 response should mention owner/admin."""
        src = self._get_function_source("assign_subscription_to_agent")
        assert "403" in src, "Must raise 403 on unauthorized access"
        # Ensure the error message is informative
        lower_src = src.lower()
        assert "owner" in lower_src or "admin" in lower_src, (
            "403 detail should mention owner or admin requirement"
        )

    # ---- DELETE /api/subscriptions/agents/{name} ----

    def test_clear_uses_can_user_share_agent(self):
        """clear_agent_subscription must call can_user_share_agent, not can_user_access_agent."""
        src = self._get_function_source("clear_agent_subscription")
        assert "can_user_share_agent" in src, (
            "clear_agent_subscription must use can_user_share_agent (owner/admin only)"
        )
        assert "can_user_access_agent" not in src, (
            "clear_agent_subscription must NOT use can_user_access_agent (allows shared users)"
        )

    def test_clear_returns_403_message(self):
        """clear_agent_subscription 403 response should mention owner/admin."""
        src = self._get_function_source("clear_agent_subscription")
        assert "403" in src
        lower_src = src.lower()
        assert "owner" in lower_src or "admin" in lower_src

    # ---- GET /api/subscriptions/agents/{name}/auth (read-only, should remain permissive) ----

    def test_auth_status_still_uses_can_user_access_agent(self):
        """get_agent_auth_status should still use can_user_access_agent (read-only endpoint)."""
        src = self._get_function_source("get_agent_auth_status")
        assert "can_user_access_agent" in src, (
            "get_agent_auth_status is read-only and should allow shared users"
        )
        assert "can_user_share_agent" not in src, (
            "get_agent_auth_status should NOT restrict to owners only"
        )

    # ---- Global: no regression ----

    def test_no_can_user_access_agent_in_mutation_endpoints(self):
        """Ensure can_user_access_agent is NOT used anywhere in assign or clear functions."""
        for func_name in ["assign_subscription_to_agent", "clear_agent_subscription"]:
            src = self._get_function_source(func_name)
            assert "can_user_access_agent" not in src, (
                f"{func_name} must not use can_user_access_agent — "
                f"this was the BOLA vulnerability in Issue #182"
            )

    def test_mutation_endpoints_have_authorization_check(self):
        """Both mutation endpoints must have an explicit authorization check."""
        for func_name in ["assign_subscription_to_agent", "clear_agent_subscription"]:
            src = self._get_function_source(func_name)
            assert "can_user_share_agent" in src, (
                f"{func_name} is missing authorization check"
            )
            assert "HTTPException" in src, (
                f"{func_name} must raise HTTPException on auth failure"
            )
