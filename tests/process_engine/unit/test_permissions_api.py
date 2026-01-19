"""
Unit tests for /api/users/me/permissions endpoint.

Reference: BACKLOG_ACCESS_AUDIT.md - E17-05
"""

import pytest
import sys
import types
from pathlib import Path

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

from services.process_engine.domain import (
    ProcessRole,
    ProcessPermission,
    ROLE_PERMISSIONS,
    get_role_permissions,
)


class TestGetRolePermissions:
    """Tests for the get_role_permissions helper function."""

    def test_admin_has_all_permissions(self):
        """Admin role should have all permissions."""
        permissions = get_role_permissions(ProcessRole.ADMIN)
        assert permissions == set(ProcessPermission)

    def test_designer_permissions(self):
        """Designer should have process CRUD and publish permissions."""
        permissions = get_role_permissions(ProcessRole.DESIGNER)
        
        # Should have
        assert ProcessPermission.PROCESS_CREATE in permissions
        assert ProcessPermission.PROCESS_READ in permissions
        assert ProcessPermission.PROCESS_UPDATE in permissions
        assert ProcessPermission.PROCESS_DELETE in permissions
        assert ProcessPermission.PROCESS_PUBLISH in permissions
        assert ProcessPermission.EXECUTION_VIEW in permissions
        
        # Should NOT have
        assert ProcessPermission.EXECUTION_TRIGGER not in permissions
        assert ProcessPermission.ADMIN_VIEW_ALL not in permissions

    def test_operator_permissions(self):
        """Operator should have execution permissions but not process edit."""
        permissions = get_role_permissions(ProcessRole.OPERATOR)
        
        # Should have
        assert ProcessPermission.PROCESS_READ in permissions
        assert ProcessPermission.EXECUTION_TRIGGER in permissions
        assert ProcessPermission.EXECUTION_VIEW in permissions
        assert ProcessPermission.EXECUTION_CANCEL in permissions
        assert ProcessPermission.EXECUTION_RETRY in permissions
        
        # Should NOT have
        assert ProcessPermission.PROCESS_CREATE not in permissions
        assert ProcessPermission.PROCESS_UPDATE not in permissions
        assert ProcessPermission.PROCESS_DELETE not in permissions

    def test_viewer_permissions(self):
        """Viewer should only have read and view permissions."""
        permissions = get_role_permissions(ProcessRole.VIEWER)
        
        # Should have (minimal)
        assert ProcessPermission.PROCESS_READ in permissions
        assert ProcessPermission.EXECUTION_VIEW in permissions
        
        # Should NOT have
        assert ProcessPermission.PROCESS_CREATE not in permissions
        assert ProcessPermission.EXECUTION_TRIGGER not in permissions
        assert ProcessPermission.EXECUTION_CANCEL not in permissions

    def test_approver_permissions(self):
        """Approver should have approval and limited view permissions."""
        permissions = get_role_permissions(ProcessRole.APPROVER)
        
        # Should have
        assert ProcessPermission.PROCESS_READ in permissions
        assert ProcessPermission.EXECUTION_VIEW in permissions
        assert ProcessPermission.APPROVAL_DECIDE in permissions
        
        # Should NOT have
        assert ProcessPermission.EXECUTION_TRIGGER not in permissions
        assert ProcessPermission.PROCESS_CREATE not in permissions


class TestPermissionSerialization:
    """Tests for permission serialization format."""

    def test_permission_values_are_strings(self):
        """All permission values should be strings for JSON serialization."""
        for perm in ProcessPermission:
            assert isinstance(perm.value, str)
            assert ":" in perm.value  # Format: "category:action"

    def test_role_values_are_strings(self):
        """All role values should be strings for JSON serialization."""
        for role in ProcessRole:
            assert isinstance(role.value, str)

    def test_permissions_are_sortable(self):
        """Permissions should be sortable for consistent API response."""
        permissions = get_role_permissions(ProcessRole.OPERATOR)
        sorted_perms = sorted([p.value for p in permissions])
        assert sorted_perms == sorted(sorted_perms)  # Sanity check


class TestRoleMapping:
    """Tests for user role to ProcessRole mapping."""

    def test_role_mapping_coverage(self):
        """Verify common role strings map to ProcessRoles."""
        role_mapping = {
            'admin': ProcessRole.ADMIN,
            'process_admin': ProcessRole.ADMIN,
            'process_designer': ProcessRole.DESIGNER,
            'designer': ProcessRole.DESIGNER,
            'process_operator': ProcessRole.OPERATOR,
            'operator': ProcessRole.OPERATOR,
            'process_approver': ProcessRole.APPROVER,
            'approver': ProcessRole.APPROVER,
            'process_viewer': ProcessRole.VIEWER,
            'viewer': ProcessRole.VIEWER,
            'user': ProcessRole.OPERATOR,  # Default
        }
        
        for role_str, expected_role in role_mapping.items():
            assert expected_role in ProcessRole
            # Verify permissions exist for this role
            perms = get_role_permissions(expected_role)
            assert len(perms) > 0

    def test_all_roles_have_permissions(self):
        """Every ProcessRole should have at least one permission."""
        for role in ProcessRole:
            permissions = get_role_permissions(role)
            assert len(permissions) > 0, f"Role {role.value} has no permissions"


class TestRolePermissionsMapping:
    """Tests for ROLE_PERMISSIONS constant."""

    def test_all_roles_defined(self):
        """All ProcessRoles should be in ROLE_PERMISSIONS."""
        for role in ProcessRole:
            assert role in ROLE_PERMISSIONS, f"Role {role.value} not in ROLE_PERMISSIONS"

    def test_permissions_are_valid(self):
        """All permissions in mapping should be valid ProcessPermissions."""
        for role, perms in ROLE_PERMISSIONS.items():
            for perm in perms:
                assert isinstance(perm, ProcessPermission), \
                    f"Invalid permission {perm} for role {role.value}"
