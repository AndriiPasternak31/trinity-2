"""
User Management API - Admin only endpoints.

Provides user listing and role management for administrators.

Reference: BACKLOG_ACCESS_AUDIT.md - E17-06
"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from models import User
from dependencies import get_current_user
from database import db
from services.process_engine.domain import ProcessRole
from services.process_engine.services import ProcessAuthorizationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/users", tags=["admin-users"])


# ============================================================================
# Request/Response Models
# ============================================================================

class UserResponse(BaseModel):
    """User data returned by API."""
    id: int
    username: str
    email: Optional[str] = None
    name: Optional[str] = None
    role: str
    created_at: Optional[str] = None
    last_login: Optional[str] = None


class UserListResponse(BaseModel):
    """Response for listing users."""
    users: List[UserResponse]
    total: int


class RoleUpdateRequest(BaseModel):
    """Request to update a user's role."""
    role: str = Field(..., description="New role for the user")


class RoleUpdateResponse(BaseModel):
    """Response after role update."""
    id: int
    username: str
    role: str
    previous_role: str
    updated_at: str


# ============================================================================
# Helper Functions
# ============================================================================

def get_auth_service() -> ProcessAuthorizationService:
    """Get authorization service instance."""
    return ProcessAuthorizationService()


def require_admin(
    current_user: User = Depends(get_current_user),
    auth_service: ProcessAuthorizationService = Depends(get_auth_service)
) -> User:
    """
    Dependency that requires the current user to be an admin.
    
    Raises 403 if user is not admin.
    """
    if not auth_service.is_admin(current_user):
        logger.warning(f"Non-admin user {current_user.username} attempted admin action")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def validate_role(role: str) -> ProcessRole:
    """
    Validate that a role string is a valid ProcessRole.
    
    Returns the ProcessRole enum member.
    Raises HTTPException if invalid.
    """
    valid_roles = {r.value: r for r in ProcessRole}
    
    if role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{role}'. Valid roles: {list(valid_roles.keys())}"
        )
    
    return valid_roles[role]


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("", response_model=UserListResponse)
async def list_users(
    admin_user: User = Depends(require_admin)
):
    """
    List all users in the system.
    
    Requires admin role.
    """
    users_data = db.list_users()
    
    users = [
        UserResponse(
            id=u["id"],
            username=u["username"],
            email=u.get("email"),
            name=u.get("name"),
            role=u["role"],
            created_at=u.get("created_at"),
            last_login=u.get("last_login")
        )
        for u in users_data
    ]
    
    logger.info(f"Admin {admin_user.username} listed {len(users)} users")
    
    return UserListResponse(users=users, total=len(users))


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    admin_user: User = Depends(require_admin)
):
    """
    Get a specific user by ID.
    
    Requires admin role.
    """
    user_data = db.get_user_by_id(user_id)
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    return UserResponse(
        id=user_data["id"],
        username=user_data["username"],
        email=user_data.get("email"),
        name=user_data.get("name"),
        role=user_data["role"],
        created_at=user_data.get("created_at"),
        last_login=user_data.get("last_login")
    )


@router.put("/{user_id}/role", response_model=RoleUpdateResponse)
async def update_user_role(
    user_id: int,
    request: RoleUpdateRequest,
    admin_user: User = Depends(require_admin)
):
    """
    Update a user's role.
    
    Requires admin role.
    Cannot change your own role (to prevent admin lockout).
    """
    # Validate the new role
    new_role = validate_role(request.role)
    
    # Get the user to update
    user_data = db.get_user_by_id(user_id)
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Prevent admin from changing their own role
    if user_data["username"] == admin_user.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role"
        )
    
    previous_role = user_data["role"]
    
    # Update the role
    updated_user = db.update_user(user_data["username"], {"role": new_role.value})
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user role"
        )
    
    logger.info(
        f"Admin {admin_user.username} changed role of {user_data['username']} "
        f"from {previous_role} to {new_role.value}"
    )
    
    return RoleUpdateResponse(
        id=user_id,
        username=user_data["username"],
        role=new_role.value,
        previous_role=previous_role,
        updated_at=datetime.utcnow().isoformat() + "Z"
    )


@router.get("/roles/available")
async def get_available_roles(
    admin_user: User = Depends(require_admin)
):
    """
    Get list of available roles with descriptions.
    
    Requires admin role.
    """
    from services.process_engine.domain import get_role_permissions
    
    roles = []
    for role in ProcessRole:
        permissions = get_role_permissions(role)
        roles.append({
            "value": role.value,
            "name": role.name.replace('_', ' ').title(),
            "description": _get_role_description(role),
            "permission_count": len(permissions)
        })
    
    return {"roles": roles}


def _get_role_description(role: ProcessRole) -> str:
    """Get a human-readable description for a role."""
    descriptions = {
        ProcessRole.ADMIN: "Full access to all operations including user management",
        ProcessRole.DESIGNER: "Can create, edit, and publish process definitions",
        ProcessRole.OPERATOR: "Can trigger and manage executions",
        ProcessRole.VIEWER: "Read-only access to processes and own executions",
        ProcessRole.APPROVER: "Can decide on approval steps assigned to them",
    }
    return descriptions.get(role, "No description available")
