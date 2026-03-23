"""
Base classes for channel adapter abstraction.

ChannelAdapter: message processing interface (parse incoming, send outgoing)
NormalizedMessage: channel-agnostic incoming message
ChannelResponse: channel-agnostic outgoing response

Each channel (Slack, Telegram, etc.) implements ChannelAdapter.
Transport details (webhook vs socket vs polling) are handled separately
in adapters/transports/.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from pydantic import BaseModel


class NormalizedMessage(BaseModel):
    """Channel-agnostic incoming message."""
    sender_id: str                      # Channel-specific user ID
    text: str                           # Message content
    channel_id: str                     # Conversation/channel identifier
    thread_id: Optional[str] = None     # Thread ID (Slack thread_ts, Telegram reply_to)
    timestamp: str                      # ISO timestamp
    metadata: dict = {}                 # Channel-specific extras (team_id, bot_token, etc.)


class ChannelResponse(BaseModel):
    """Channel-agnostic outgoing response."""
    text: str                           # Response content (may contain markdown)
    metadata: dict = {}                 # Extra context (agent_name, cost, etc.)


class ChannelAdapter(ABC):
    """
    Message processing interface — transport-agnostic.

    Each channel implements this to handle:
    - Parsing raw events into NormalizedMessage
    - Sending responses back through the channel
    - Resolving which agent handles the message

    Channel-specific concerns (verification, rich formatting, identity overrides)
    live on the concrete adapter, not here.
    """

    @abstractmethod
    def parse_message(self, raw_event: dict) -> Optional[NormalizedMessage]:
        """
        Extract NormalizedMessage from a raw channel event.

        Returns None to skip the event (bot messages, unsupported types, etc.)
        """

    @abstractmethod
    async def send_response(
        self,
        channel_id: str,
        response: ChannelResponse,
        thread_id: Optional[str] = None
    ) -> None:
        """Deliver a response back to the channel."""

    @abstractmethod
    async def get_agent_name(self, message: NormalizedMessage) -> Optional[str]:
        """
        Resolve which Trinity agent should handle this message.

        Returns agent name, or None if no agent is configured for this channel/user.
        """
