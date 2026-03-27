"""
Unit tests for subscription endpoint authorization (issue #182).

Verifies that PUT/DELETE subscription assignment endpoints require
owner/admin access (can_user_share_agent), not just read access
(can_user_access_agent). Shared users must receive HTTP 403.

Uses importlib to load the subscriptions module directly, bypassing
the routers package __init__.py import chain that requires jose.
"""

import pytest
import sys
import os
import asyncio
import importlib.util
from unittest.mock import Mock, MagicMock, patch

# Add backend path for imports
backend_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "src", "backend")
)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


def load_subscriptions_module(mock_db):
    """Load subscriptions router with mocked database to avoid import chain.

    db_models and models load fine natively (Pydantic models).
    Only 'dependencies' needs mocking (requires jose for JWT).
    """
    # Mock modules that have deep import chains we can't satisfy in test env.
    # We need: dependencies (jose), models (utils.helpers), database (db instance)
    mock_deps = Mock()
    mock_deps.get_current_user = Mock()
    mock_deps.require_admin = Mock()

    mock_models = Mock()
    mock_models.User = Mock  # Type annotation only — any class works

    mock_database = Mock()
    mock_database.db = mock_db

    saved_modules = {}
    mocks = {
        "dependencies": mock_deps,
        "database": mock_database,
        "models": mock_models,
        "utils": Mock(),
        "utils.helpers": Mock(),
    }

    for mod_name, mock_mod in mocks.items():
        saved_modules[mod_name] = sys.modules.get(mod_name)
        sys.modules[mod_name] = mock_mod

    try:
        # Clear cached module
        for key in list(sys.modules.keys()):
            if "subscriptions" in key:
                del sys.modules[key]

        spec = importlib.util.spec_from_file_location(
            "subscriptions",
            os.path.join(backend_path, "routers", "subscriptions.py"),
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Re-bind db after module exec (overrides `from database import db`)
        module.db = mock_db

        return module
    finally:
        # Restore original modules
        for mod_name, original in saved_modules.items():
            if original is None:
                sys.modules.pop(mod_name, None)
            else:
                sys.modules[mod_name] = original


@pytest.fixture
def mock_db():
    """Create a mock database with configurable auth predicates."""
    mock = MagicMock()
    mock.get_subscription_by_name.return_value = MagicMock(
        id="sub-123", name="test-sub"
    )
    mock.get_agent_subscription.return_value = MagicMock(name="test-sub")
    mock.assign_subscription_to_agent.return_value = None
    mock.clear_agent_subscription.return_value = None
    return mock


@pytest.fixture
def shared_user():
    """A non-admin user who has shared (read-only) access to an agent."""
    user = Mock()
    user.username = "shared-user"
    user.role = "user"
    user.id = "user-456"
    return user


@pytest.fixture
def owner_user():
    """An owner user who has full access to their agent."""
    user = Mock()
    user.username = "owner-user"
    user.role = "user"
    user.id = "user-789"
    return user


@pytest.mark.unit
class TestSharedUserCannotManageSubscriptions:
    """Issue #182: Shared users must get 403 on subscription mutation endpoints."""

    def test_shared_user_cannot_assign_subscription(self, mock_db, shared_user):
        """PUT /api/subscriptions/agents/{name} returns 403 for shared users."""
        mock_db.can_user_share_agent.return_value = False

        subs = load_subscriptions_module(mock_db)

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                subs.assign_subscription_to_agent(
                    agent_name="test-agent",
                    subscription_name="test-sub",
                    current_user=shared_user,
                )
            )

        assert exc_info.value.status_code == 403
        mock_db.can_user_share_agent.assert_called_once_with(
            "shared-user", "test-agent"
        )
        # The permissive predicate must NOT be used for mutations
        mock_db.can_user_access_agent.assert_not_called()

    def test_shared_user_cannot_clear_subscription(self, mock_db, shared_user):
        """DELETE /api/subscriptions/agents/{name} returns 403 for shared users."""
        mock_db.can_user_share_agent.return_value = False

        subs = load_subscriptions_module(mock_db)

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                subs.clear_agent_subscription(
                    agent_name="test-agent",
                    current_user=shared_user,
                )
            )

        assert exc_info.value.status_code == 403
        mock_db.can_user_share_agent.assert_called_once_with(
            "shared-user", "test-agent"
        )
        mock_db.can_user_access_agent.assert_not_called()


@pytest.mark.unit
class TestOwnerCanManageSubscriptions:
    """Verify owners still have full subscription management access."""

    def test_owner_can_assign_subscription(self, mock_db, owner_user):
        """PUT /api/subscriptions/agents/{name} succeeds for owners."""
        mock_db.can_user_share_agent.return_value = True

        subs = load_subscriptions_module(mock_db)

        # Mock the lazy imports inside the handler (docker service calls)
        with patch.dict("sys.modules", {
            "services.docker_service": Mock(
                get_agent_container=Mock(return_value=None),
                get_agent_status_from_container=Mock(),
            ),
            "services.docker_utils": Mock(),
            "services.agent_service": Mock(),
        }):
            result = asyncio.get_event_loop().run_until_complete(
                subs.assign_subscription_to_agent(
                    agent_name="test-agent",
                    subscription_name="test-sub",
                    current_user=owner_user,
                )
            )

        assert result["success"] is True
        assert result["subscription_name"] == "test-sub"
        mock_db.can_user_share_agent.assert_called_once_with(
            "owner-user", "test-agent"
        )

    def test_owner_can_clear_subscription(self, mock_db, owner_user):
        """DELETE /api/subscriptions/agents/{name} succeeds for owners."""
        mock_db.can_user_share_agent.return_value = True

        subs = load_subscriptions_module(mock_db)

        # Mock lazy imports for docker services (clear handler restarts agent)
        mock_docker_svc = Mock()
        mock_docker_svc.get_agent_container = Mock(return_value=None)
        mock_docker_svc.get_agent_status_from_container = Mock()
        with patch.dict("sys.modules", {
            "services": Mock(),
            "services.docker_service": mock_docker_svc,
            "services.docker_utils": Mock(),
            "services.agent_service": Mock(),
        }):
            result = asyncio.get_event_loop().run_until_complete(
                subs.clear_agent_subscription(
                    agent_name="test-agent",
                    current_user=owner_user,
                )
            )

        assert result["success"] is True
        mock_db.can_user_share_agent.assert_called_once_with(
            "owner-user", "test-agent"
        )
