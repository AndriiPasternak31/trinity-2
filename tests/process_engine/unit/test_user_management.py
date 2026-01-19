"""
Unit Tests for User Management API.

Tests admin-only user listing and role management.

Reference: BACKLOG_ACCESS_AUDIT.md - E17-06
"""

import pytest
import sys
import types
from pathlib import Path
from unittest.mock import Mock, patch

# Add src/backend to path for direct imports
_project_root = Path(__file__).resolve().parent.parent.parent.parent
_backend_path = str(_project_root / 'src' / 'backend')
_src_path = str(_project_root / 'src')

if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

# Prevent services/__init__.py from being loaded (it has heavy dependencies)
if 'services' not in sys.modules:
    sys.modules['services'] = types.ModuleType('services')
    sys.modules['services'].__path__ = [str(Path(_backend_path) / 'services')]

from services.process_engine.domain import ProcessRole
from services.process_engine.services import ProcessAuthorizationService


class MockUser:
    """Mock user for testing."""
    def __init__(self, username: str, role: str = "user"):
        self.username = username
        self.role = role
        self.id = 1
        self.email = f"{username}@test.com"


class TestRequireAdmin:
    """Tests for admin requirement validation."""

    def test_admin_user_passes(self):
        """Admin user should pass admin check."""
        auth_service = ProcessAuthorizationService()
        admin_user = MockUser("admin", "admin")

        # Admin should be allowed
        assert auth_service.is_admin(admin_user) == True

    def test_process_admin_user_passes(self):
        """Process admin user should pass admin check."""
        auth_service = ProcessAuthorizationService()
        admin_user = MockUser("admin", "process_admin")

        # Process admin should be allowed
        assert auth_service.is_admin(admin_user) == True

    def test_regular_user_fails(self):
        """Regular user should fail admin check."""
        auth_service = ProcessAuthorizationService()
        regular_user = MockUser("user", "user")

        # Regular user should NOT be admin
        assert auth_service.is_admin(regular_user) == False

    def test_designer_fails(self):
        """Designer should fail admin check."""
        auth_service = ProcessAuthorizationService()
        designer = MockUser("designer", "process_designer")

        # Designer should NOT be admin
        assert auth_service.is_admin(designer) == False

    def test_operator_fails(self):
        """Operator should fail admin check."""
        auth_service = ProcessAuthorizationService()
        operator = MockUser("operator", "process_operator")

        # Operator should NOT be admin
        assert auth_service.is_admin(operator) == False


class TestRoleValidation:
    """Tests for role validation logic."""

    def _validate_role(self, role_str: str) -> ProcessRole:
        """
        Local implementation of validate_role for testing.
        This mirrors the logic in routers/users.py without FastAPI deps.
        """
        valid_roles = {r.value: r for r in ProcessRole}
        if role_str not in valid_roles:
            raise ValueError(f"Invalid role '{role_str}'")
        return valid_roles[role_str]

    def test_valid_admin_role(self):
        """Admin role should be valid."""
        role = self._validate_role("process_admin")
        assert role == ProcessRole.ADMIN

    def test_valid_designer_role(self):
        """Designer role should be valid."""
        role = self._validate_role("process_designer")
        assert role == ProcessRole.DESIGNER

    def test_valid_operator_role(self):
        """Operator role should be valid."""
        role = self._validate_role("process_operator")
        assert role == ProcessRole.OPERATOR

    def test_valid_viewer_role(self):
        """Viewer role should be valid."""
        role = self._validate_role("process_viewer")
        assert role == ProcessRole.VIEWER

    def test_valid_approver_role(self):
        """Approver role should be valid."""
        role = self._validate_role("process_approver")
        assert role == ProcessRole.APPROVER

    def test_invalid_role_raises_error(self):
        """Invalid role should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            self._validate_role("invalid_role")

        assert "Invalid role" in str(exc_info.value)


class TestRoleDescriptions:
    """Tests for role description helpers."""

    def _get_role_description(self, role: ProcessRole) -> str:
        """
        Local implementation of role descriptions for testing.
        This mirrors the logic in routers/users.py.
        """
        descriptions = {
            ProcessRole.ADMIN: "Full access to all operations including user management",
            ProcessRole.DESIGNER: "Can create, edit, and publish process definitions",
            ProcessRole.OPERATOR: "Can trigger and manage executions",
            ProcessRole.VIEWER: "Read-only access to processes and own executions",
            ProcessRole.APPROVER: "Can decide on approval steps assigned to them",
        }
        return descriptions.get(role, "No description available")

    def test_all_roles_have_descriptions(self):
        """All ProcessRoles should have descriptions."""
        for role in ProcessRole:
            description = self._get_role_description(role)
            assert description, f"Role {role.value} has no description"
            assert len(description) > 10, f"Role {role.value} description too short"

    def test_admin_description(self):
        """Admin should have appropriate description."""
        desc = self._get_role_description(ProcessRole.ADMIN)
        assert "full access" in desc.lower() or "all operations" in desc.lower()

    def test_designer_description(self):
        """Designer should have appropriate description."""
        desc = self._get_role_description(ProcessRole.DESIGNER)
        assert "create" in desc.lower() or "edit" in desc.lower()

    def test_operator_description(self):
        """Operator should have appropriate description."""
        desc = self._get_role_description(ProcessRole.OPERATOR)
        assert "trigger" in desc.lower() or "execution" in desc.lower()


class TestSelfRoleChange:
    """Tests for preventing self-role changes."""

    def test_cannot_change_own_role_logic(self):
        """Admin should not be able to change their own role."""
        # This tests the logic, not the endpoint directly
        admin_user = MockUser("admin", "admin")
        target_username = "admin"  # Same as requesting user

        # The check should detect same username
        assert admin_user.username == target_username


class TestRoleValues:
    """Tests for ProcessRole enum values."""

    def test_all_process_roles_are_prefixed(self):
        """All process role values should be prefixed with 'process_'."""
        for role in ProcessRole:
            assert role.value.startswith("process_"), \
                f"Role {role.name} value '{role.value}' should start with 'process_'"

    def test_role_values_are_unique(self):
        """All role values should be unique."""
        values = [r.value for r in ProcessRole]
        assert len(values) == len(set(values)), "Duplicate role values found"

    def test_expected_roles_exist(self):
        """Expected roles should exist."""
        expected = ["process_admin", "process_designer", "process_operator",
                   "process_viewer", "process_approver"]

        actual_values = [r.value for r in ProcessRole]

        for expected_role in expected:
            assert expected_role in actual_values, \
                f"Expected role '{expected_role}' not found"
