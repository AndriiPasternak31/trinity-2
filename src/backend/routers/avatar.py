"""
Avatar generation and serving router (AVATAR-001, AVATAR-002).

REST endpoints for AI-generated agent avatars and emotion variants.
"""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from database import db
from dependencies import get_current_user
from models import User
from services.image_generation_prompts import AVATAR_EMOTIONS, AVATAR_EMOTION_PROMPTS
from services.image_generation_service import get_image_generation_service

router = APIRouter(prefix="/api/agents", tags=["avatars"])
logger = logging.getLogger(__name__)

AVATAR_DIR = Path("/data/avatars")


class AvatarGenerateRequest(BaseModel):
    identity_prompt: str


@router.get("/{agent_name}/avatar")
async def get_avatar(agent_name: str):
    """Serve cached avatar PNG for an agent. No auth required — avatars are public assets."""
    avatar_path = AVATAR_DIR / f"{agent_name}.png"
    if not avatar_path.exists():
        raise HTTPException(status_code=404, detail="No avatar found")

    return FileResponse(
        avatar_path,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/{agent_name}/avatar/reference")
async def get_avatar_reference(agent_name: str):
    """Serve reference avatar PNG for an agent. No auth required — avatars are public assets."""
    ref_path = AVATAR_DIR / f"{agent_name}_ref.png"
    if not ref_path.exists():
        raise HTTPException(status_code=404, detail="No reference image found")

    return FileResponse(
        ref_path,
        media_type="image/png",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/{agent_name}/avatar/identity")
async def get_avatar_identity(
    agent_name: str,
    current_user: User = Depends(get_current_user),
):
    """Return avatar identity prompt and metadata."""
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="Access denied")

    identity = db.get_avatar_identity(agent_name)
    avatar_path = AVATAR_DIR / f"{agent_name}.png"
    ref_path = AVATAR_DIR / f"{agent_name}_ref.png"

    return {
        "agent_name": agent_name,
        "identity_prompt": identity["identity_prompt"] if identity else None,
        "updated_at": identity["updated_at"] if identity else None,
        "has_avatar": avatar_path.exists(),
        "has_reference": ref_path.exists(),
    }


async def _generate_emotions_background(
    agent_name: str,
    reference_bytes: bytes,
    identity_prompt: str,
):
    """Generate 8 emotion variants in the background (fire-and-forget).

    Iterates sequentially to avoid API rate limits. Each failure is logged
    but does not stop the loop. If the reference file changes or disappears
    mid-loop the task aborts.
    """
    service = get_image_generation_service()
    ref_path = AVATAR_DIR / f"{agent_name}_ref.png"

    logger.info(f"[AVATAR-002] Starting background emotion generation for {agent_name}")

    for emotion in AVATAR_EMOTIONS:
        # Guard: abort if reference was deleted or replaced
        if not ref_path.exists() or ref_path.read_bytes() != reference_bytes:
            logger.info(
                f"[AVATAR-002] Reference changed for {agent_name}, aborting emotion generation"
            )
            return

        expression = AVATAR_EMOTION_PROMPTS[emotion]
        emotion_prompt = (
            f"Generate a portrait of this exact same subject with the following "
            f"facial expression: {expression}. Keep the same identity, features, "
            f"clothing, and style. Only change the expression/emotion. "
            f"Original character: {identity_prompt}"
        )

        try:
            result = await service.generate_emotion_variation(
                emotion_prompt=emotion_prompt,
                reference_image=reference_bytes,
                aspect_ratio="1:1",
                agent_name=agent_name,
            )
            if result.success and result.image_data:
                emotion_path = AVATAR_DIR / f"{agent_name}_emotion_{emotion}.png"
                emotion_path.write_bytes(result.image_data)
                logger.info(
                    f"[AVATAR-002] Saved emotion '{emotion}' for {agent_name}: "
                    f"{len(result.image_data)} bytes"
                )
            else:
                logger.warning(
                    f"[AVATAR-002] Emotion '{emotion}' failed for {agent_name}: "
                    f"{result.error}"
                )
        except Exception as e:
            logger.warning(
                f"[AVATAR-002] Emotion '{emotion}' error for {agent_name}: {e}"
            )

    logger.info(f"[AVATAR-002] Finished emotion generation for {agent_name}")


@router.get("/{agent_name}/avatar/emotions")
async def get_avatar_emotions(agent_name: str):
    """Return which emotion variant PNGs exist on disk for an agent. No auth required."""
    available = []
    for emotion in AVATAR_EMOTIONS:
        if (AVATAR_DIR / f"{agent_name}_emotion_{emotion}.png").exists():
            available.append(emotion)
    return {"agent_name": agent_name, "emotions": available}


@router.get("/{agent_name}/avatar/emotion/{emotion}")
async def get_avatar_emotion(agent_name: str, emotion: str):
    """Serve an emotion variant PNG. No auth required."""
    if emotion not in AVATAR_EMOTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid emotion. Must be one of: {AVATAR_EMOTIONS}",
        )

    emotion_path = AVATAR_DIR / f"{agent_name}_emotion_{emotion}.png"
    if not emotion_path.exists():
        raise HTTPException(status_code=404, detail="Emotion variant not found")

    return FileResponse(
        emotion_path,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.post("/{agent_name}/avatar/generate")
async def generate_avatar(
    agent_name: str,
    request: AvatarGenerateRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate an avatar from an identity prompt using the image generation service."""
    # Only owner/admin can generate
    owner = db.get_agent_owner(agent_name)
    if not owner:
        raise HTTPException(status_code=404, detail="Agent not found")

    is_admin = current_user.role == "admin"
    is_owner = owner["owner_username"] == current_user.username
    if not (is_admin or is_owner):
        raise HTTPException(status_code=403, detail="Only the agent owner can generate avatars")

    identity_prompt = request.identity_prompt.strip()
    if not identity_prompt:
        raise HTTPException(status_code=400, detail="identity_prompt cannot be empty")

    if len(identity_prompt) > 500:
        raise HTTPException(status_code=400, detail="identity_prompt must be 500 characters or less")

    service = get_image_generation_service()
    if not service.available:
        raise HTTPException(
            status_code=501,
            detail="Image generation not available: GEMINI_API_KEY not configured",
        )

    result = await service.generate_image(
        prompt=identity_prompt,
        use_case="avatar",
        aspect_ratio="1:1",
        refine_prompt=True,
        agent_name=agent_name,
    )

    if not result.success:
        raise HTTPException(status_code=422, detail=result.error)

    # Save avatar and reference image to disk
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    avatar_path = AVATAR_DIR / f"{agent_name}.png"
    ref_path = AVATAR_DIR / f"{agent_name}_ref.png"
    avatar_path.write_bytes(result.image_data)
    ref_path.write_bytes(result.image_data)  # First generation = reference

    # Delete any existing emotion files (AVATAR-002) — new reference invalidates them
    for emotion in AVATAR_EMOTIONS:
        ep = AVATAR_DIR / f"{agent_name}_emotion_{emotion}.png"
        if ep.exists():
            ep.unlink()

    # Kick off background emotion generation (AVATAR-002)
    asyncio.create_task(
        _generate_emotions_background(agent_name, result.image_data, identity_prompt)
    )

    # Update DB
    now = datetime.now(timezone.utc).isoformat()
    db.set_avatar_identity(agent_name, identity_prompt, now)

    logger.info(f"Generated avatar + reference for agent {agent_name}: {len(result.image_data)} bytes")

    return {
        "agent_name": agent_name,
        "identity_prompt": identity_prompt,
        "refined_prompt": result.refined_prompt,
        "updated_at": now,
    }


@router.post("/{agent_name}/avatar/regenerate")
async def regenerate_avatar(
    agent_name: str,
    current_user: User = Depends(get_current_user),
):
    """Regenerate avatar as a variation of the reference image."""
    owner = db.get_agent_owner(agent_name)
    if not owner:
        raise HTTPException(status_code=404, detail="Agent not found")

    is_admin = current_user.role == "admin"
    is_owner = owner["owner_username"] == current_user.username
    if not (is_admin or is_owner):
        raise HTTPException(status_code=403, detail="Only the agent owner can regenerate avatars")

    # Need a reference image and stored prompt
    ref_path = AVATAR_DIR / f"{agent_name}_ref.png"
    if not ref_path.exists():
        raise HTTPException(status_code=404, detail="No reference image found. Generate an avatar first.")

    identity = db.get_avatar_identity(agent_name)
    if not identity or not identity.get("identity_prompt"):
        raise HTTPException(status_code=404, detail="No identity prompt found. Generate an avatar first.")

    service = get_image_generation_service()
    if not service.available:
        raise HTTPException(
            status_code=501,
            detail="Image generation not available: GEMINI_API_KEY not configured",
        )

    reference_bytes = ref_path.read_bytes()
    result = await service.generate_variation(
        prompt=identity["identity_prompt"],
        reference_image=reference_bytes,
        aspect_ratio="1:1",
        agent_name=agent_name,
    )

    if not result.success:
        raise HTTPException(status_code=422, detail=result.error)

    # Save as display avatar only (reference stays the same)
    avatar_path = AVATAR_DIR / f"{agent_name}.png"
    avatar_path.write_bytes(result.image_data)

    now = datetime.now(timezone.utc).isoformat()
    db.set_avatar_identity(agent_name, identity["identity_prompt"], now)

    logger.info(f"Regenerated avatar from reference for agent {agent_name}: {len(result.image_data)} bytes")

    return {
        "agent_name": agent_name,
        "identity_prompt": identity["identity_prompt"],
        "updated_at": now,
    }


@router.delete("/{agent_name}/avatar")
async def delete_avatar(
    agent_name: str,
    current_user: User = Depends(get_current_user),
):
    """Remove avatar file and clear DB fields."""
    owner = db.get_agent_owner(agent_name)
    if not owner:
        raise HTTPException(status_code=404, detail="Agent not found")

    is_admin = current_user.role == "admin"
    is_owner = owner["owner_username"] == current_user.username
    if not (is_admin or is_owner):
        raise HTTPException(status_code=403, detail="Only the agent owner can remove avatars")

    # Delete files (display + reference + emotion variants)
    avatar_path = AVATAR_DIR / f"{agent_name}.png"
    ref_path = AVATAR_DIR / f"{agent_name}_ref.png"
    if avatar_path.exists():
        avatar_path.unlink()
    if ref_path.exists():
        ref_path.unlink()
    for emotion in AVATAR_EMOTIONS:
        ep = AVATAR_DIR / f"{agent_name}_emotion_{emotion}.png"
        if ep.exists():
            ep.unlink()

    # Clear DB
    db.clear_avatar_identity(agent_name)

    logger.info(f"Deleted avatar for agent {agent_name}")

    return {"message": f"Avatar removed for {agent_name}"}
