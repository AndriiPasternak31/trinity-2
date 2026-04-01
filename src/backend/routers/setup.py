"""
First-time setup routes for the Trinity backend.

Provides endpoints for initial admin password setup on first launch.
These endpoints require NO authentication and only work before setup is completed.
"""
import secrets
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from database import db
from dependencies import hash_password
from utils.password_validation import validate_password_strength, PASSWORD_REQUIREMENTS_MESSAGE

router = APIRouter(prefix="/api/setup", tags=["setup"])

# Single-use setup token generated at startup.
# Must be provided when calling POST /api/setup/admin-password.
# Prevents installation hijack: only someone with access to server logs can complete setup.
_setup_token: str = secrets.token_urlsafe(24)


def get_setup_token() -> str:
    """Return the setup token for printing during startup."""
    return _setup_token


class SetAdminPasswordRequest(BaseModel):
    """Request body for setting admin password."""
    password: str = Field(..., max_length=128)
    confirm_password: str = Field(..., max_length=128)
    setup_token: str


@router.get("/status")
async def get_setup_status():
    """
    Check if initial setup is complete. No auth required.

    Returns:
        - setup_completed: Whether the admin password has been set
    """
    setup_completed = db.get_setting_value('setup_completed', 'false') == 'true'
    return {
        "setup_completed": setup_completed
    }


@router.post("/admin-password")
async def set_admin_password(data: SetAdminPasswordRequest, request: Request):
    """
    Set admin password on first launch. No auth required, only works once.

    Requires the setup token printed to server logs at startup (prevents installation hijack).
    Once setup_completed=true is set, this endpoint returns 403.

    Requirements:
    - setup_token must match the token printed in server logs at startup
    - Password must meet OWASP ASVS 2.1 complexity requirements
    - Password and confirm_password must match

    Returns:
        - success: true if password was set
    """
    # Check setup not already completed
    if db.get_setting_value('setup_completed', 'false') == 'true':
        raise HTTPException(
            status_code=403,
            detail="Setup already completed. Password cannot be changed through this endpoint."
        )

    # Validate setup token to prevent installation hijack.
    # Use constant-time comparison to guard against timing attacks.
    if not secrets.compare_digest(data.setup_token, _setup_token):
        raise HTTPException(
            status_code=403,
            detail="Invalid setup token. Check server logs for the setup token printed at startup."
        )

    # Validate password complexity (OWASP ASVS 2.1)
    errors = validate_password_strength(data.password)
    if errors:
        # Return generic message — don't reveal which specific rules failed
        # on this unauthenticated endpoint (CSO review finding #1)
        raise HTTPException(
            status_code=400,
            detail=PASSWORD_REQUIREMENTS_MESSAGE,
        )

    if data.password != data.confirm_password:
        raise HTTPException(
            status_code=400,
            detail="Passwords do not match"
        )

    # Hash the password and update admin user
    hashed_password = hash_password(data.password)

    # Update admin user's password in database
    db.update_user_password('admin', hashed_password)

    # Mark setup as completed
    db.set_setting('setup_completed', 'true')

    return {"success": True}
