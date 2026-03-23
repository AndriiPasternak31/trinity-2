"""
Channel-agnostic message router.

Receives NormalizedMessage from any adapter, resolves the agent,
builds context, dispatches to the agent via TaskExecutionService,
persists messages, and returns the response through the adapter.

Uses the same execution path as web public chat (EXEC-024) for:
- Execution records and audit trail
- Activity tracking (Dashboard timeline)
- Slot management (capacity limits)
- Credential sanitization
"""

import logging
import time
from typing import Optional
from collections import defaultdict

from database import db
from services.docker_service import get_agent_container
from services.task_execution_service import get_task_execution_service
from adapters.base import ChannelAdapter, ChannelResponse, NormalizedMessage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Simple in-memory rate limiter
# ---------------------------------------------------------------------------

_rate_limit_buckets: dict = defaultdict(list)  # key → list of timestamps
RATE_LIMIT_MAX = 30       # messages per window
RATE_LIMIT_WINDOW = 60    # seconds


def _check_rate_limit(key: str) -> bool:
    """Returns True if allowed, False if rate limited."""
    now = time.time()
    bucket = _rate_limit_buckets[key]
    # Remove expired entries
    _rate_limit_buckets[key] = [t for t in bucket if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limit_buckets[key]) >= RATE_LIMIT_MAX:
        return False
    _rate_limit_buckets[key].append(now)
    return True


class ChannelMessageRouter:
    """Channel-agnostic message dispatcher."""

    async def handle_message(self, adapter: ChannelAdapter, message: NormalizedMessage) -> None:
        """Process an incoming message through the full pipeline."""
        try:
            await self._handle_message_inner(adapter, message)
        except Exception as e:
            logger.error(f"[ROUTER] Unhandled error in handle_message: {e}", exc_info=True)

    async def _handle_message_inner(self, adapter: ChannelAdapter, message: NormalizedMessage) -> None:
        logger.info(f"[ROUTER] START: sender={message.sender_id}, channel={message.channel_id}, is_dm={message.metadata.get('is_dm')}, team={message.metadata.get('team_id')}, text={message.text[:50]}")

        # 1. Resolve agent
        agent_name = await adapter.get_agent_name(message)
        logger.info(f"[ROUTER] Step 1 - resolved agent: {agent_name}")
        if not agent_name:
            logger.warning(f"[ROUTER] No agent found for channel {message.channel_id}")
            return

        # 2. Resolve bot token (needed for all responses)
        bot_token = self._get_bot_token(adapter, message)
        logger.info(f"[ROUTER] Step 2 - bot_token: {'yes' if bot_token else 'NO'}")
        if not bot_token:
            logger.error(f"[ROUTER] No bot token for team {message.metadata.get('team_id')}")
            return

        # 3. Rate limiting per Slack user
        rate_key = f"slack:{message.metadata.get('team_id')}:{message.sender_id}"
        if not _check_rate_limit(rate_key):
            logger.warning(f"[ROUTER] Rate limited: {rate_key}")
            await adapter.send_response(
                message.channel_id,
                ChannelResponse(
                    text="You're sending messages too quickly. Please wait a moment.",
                    metadata={"bot_token": bot_token, "agent_name": agent_name}
                ),
                thread_id=message.thread_id,
            )
            return

        # 4. Check agent availability
        container = get_agent_container(agent_name)
        container_status = container.status if container else "not_found"
        logger.info(f"[ROUTER] Step 4 - container: {container_status}")
        if not container or container.status != "running":
            await adapter.send_response(
                message.channel_id,
                ChannelResponse(
                    text="Sorry, I'm not available right now. Please try again later.",
                    metadata={"bot_token": bot_token, "agent_name": agent_name}
                ),
            )
            return

        # 5. Handle verification (Slack-specific, duck-typed)
        if hasattr(adapter, 'handle_verification'):
            logger.info(f"[ROUTER] Step 5 - running verification")
            verified = await adapter.handle_verification(message)
            logger.info(f"[ROUTER] Step 5 - verified: {verified}")
            if not verified:
                return

        # 6. Get/create session
        logger.info(f"[ROUTER] Step 6 - creating session")
        session_identifier = self._build_session_identifier(message)
        session = db.get_or_create_public_chat_session(
            agent_name, session_identifier, "slack"
        )
        session_id = session.id if hasattr(session, 'id') else session["id"]
        logger.info(f"[ROUTER] Step 6 - session_id: {session_id}")

        # 7. Build context prompt (same as web public chat)
        context_prompt = db.build_public_chat_context(session_id, message.text)
        logger.info(f"[ROUTER] Step 7 - context built ({len(context_prompt)} chars)")

        # 8. Execute via TaskExecutionService (same path as web public chat)
        logger.info(f"[ROUTER] Step 8 - executing via TaskExecutionService")
        source_email = f"slack:{message.metadata.get('team_id')}:{message.sender_id}"

        # Security: restrict tools for public Slack users
        # No file access (Read exposes .env/credentials), no Bash, no Write/Edit
        # Only web tools for research — agent answers from knowledge only
        public_allowed_tools = [
            "WebSearch",
            "WebFetch",
        ]

        try:
            task_execution_service = get_task_execution_service()
            result = await task_execution_service.execute_task(
                agent_name=agent_name,
                message=context_prompt,
                triggered_by="slack",
                source_user_email=source_email,
                timeout_seconds=120,
                allowed_tools=public_allowed_tools,
            )

            if result.status == "failed":
                error_msg = result.error or "Unknown error"
                logger.error(f"[ROUTER] Step 8 - task failed: {error_msg}")

                # User-friendly error messages
                if "at capacity" in error_msg:
                    response_text = "I'm busy right now. Please try again in a moment."
                elif "billing" in error_msg.lower() or "credit" in error_msg.lower():
                    response_text = "I'm having trouble processing your request. Please try again later."
                else:
                    response_text = "Sorry, I encountered an error processing your message."

                await adapter.send_response(
                    message.channel_id,
                    ChannelResponse(text=response_text, metadata={"bot_token": bot_token, "agent_name": agent_name}),
                    thread_id=message.thread_id,
                )
                return

            response_text = result.response or ""
            logger.info(f"[ROUTER] Step 8 - agent responded ({len(response_text)} chars, cost=${result.cost or 0:.4f})")

        except Exception as e:
            logger.error(f"[ROUTER] Step 8 - execution error: {e}", exc_info=True)
            await adapter.send_response(
                message.channel_id,
                ChannelResponse(
                    text="Sorry, I encountered an error processing your message. Please try again.",
                    metadata={"bot_token": bot_token, "agent_name": agent_name}
                ),
                thread_id=message.thread_id,
            )
            return

        # 9. Persist messages in session
        logger.info(f"[ROUTER] Step 9 - persisting messages")
        db.add_public_chat_message(session_id, "user", message.text)
        db.add_public_chat_message(session_id, "assistant", response_text, cost=result.cost)

        # 10. Send response to channel
        logger.info(f"[ROUTER] Step 10 - sending response to Slack")
        await adapter.send_response(
            message.channel_id,
            ChannelResponse(text=response_text, metadata={"bot_token": bot_token, "agent_name": agent_name}),
            thread_id=message.thread_id,
        )
        logger.info(f"[ROUTER] DONE: {agent_name}, execution_id={result.execution_id}")

    # =========================================================================
    # Private helpers
    # =========================================================================

    def _get_bot_token(self, adapter: ChannelAdapter, message: NormalizedMessage) -> Optional[str]:
        """Get bot token from adapter."""
        if hasattr(adapter, 'get_bot_token'):
            return adapter.get_bot_token(message.metadata.get("team_id"))
        return None

    def _build_session_identifier(self, message: NormalizedMessage) -> str:
        """Build a session identifier: team:user:channel for isolation."""
        team_id = message.metadata.get("team_id", "unknown")
        channel_id = message.channel_id
        return f"{team_id}:{message.sender_id}:{channel_id}"


# Singleton instance
message_router = ChannelMessageRouter()
