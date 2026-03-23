"""
Database operations for Slack multi-agent channel routing.

Handles:
- Workspace connections (one bot token per workspace)
- Channel-agent bindings (which agent responds in which channel)
"""

import secrets
from datetime import datetime
from typing import Optional, List

from db.connection import get_db_connection


class SlackChannelOperations:
    """Operations for Slack workspace connections and channel-agent bindings."""

    # =========================================================================
    # Workspace Operations
    # =========================================================================

    def create_workspace(
        self,
        team_id: str,
        team_name: Optional[str],
        bot_token: str,
        connected_by: Optional[str] = None
    ) -> dict:
        """Create or update a workspace connection."""
        workspace_id = secrets.token_urlsafe(16)
        now = datetime.utcnow().isoformat()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Upsert — update bot token if workspace already exists
            cursor.execute("""
                INSERT INTO slack_workspaces (id, team_id, team_name, bot_token, connected_by, connected_at, enabled)
                VALUES (?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(team_id) DO UPDATE SET
                    bot_token = excluded.bot_token,
                    team_name = excluded.team_name,
                    connected_at = excluded.connected_at
            """, (workspace_id, team_id, team_name, bot_token, connected_by, now))
            conn.commit()

        return self.get_workspace_by_team(team_id)

    def get_workspace_by_team(self, team_id: str) -> Optional[dict]:
        """Get workspace connection by Slack team ID."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, team_id, team_name, bot_token, connected_by, connected_at, enabled
                FROM slack_workspaces
                WHERE team_id = ? AND enabled = 1
            """, (team_id,))
            row = cursor.fetchone()

        if not row:
            return None
        return self._row_to_workspace(row)

    def get_workspace_bot_token(self, team_id: str) -> Optional[str]:
        """Get bot token for a workspace."""
        ws = self.get_workspace_by_team(team_id)
        return ws["bot_token"] if ws else None

    def delete_workspace(self, team_id: str) -> bool:
        """Delete a workspace and all its channel bindings."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM slack_channel_agents WHERE team_id = ?", (team_id,))
            cursor.execute("DELETE FROM slack_workspaces WHERE team_id = ?", (team_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
        return deleted

    # =========================================================================
    # Channel-Agent Binding Operations
    # =========================================================================

    def bind_channel_to_agent(
        self,
        team_id: str,
        slack_channel_id: str,
        slack_channel_name: Optional[str],
        agent_name: str,
        created_by: Optional[str] = None,
        is_dm_default: bool = False,
    ) -> dict:
        """Bind a Slack channel to an agent."""
        binding_id = secrets.token_urlsafe(16)
        now = datetime.utcnow().isoformat()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO slack_channel_agents
                (id, team_id, slack_channel_id, slack_channel_name, agent_name, is_dm_default, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(team_id, slack_channel_id) DO UPDATE SET
                    agent_name = excluded.agent_name,
                    slack_channel_name = excluded.slack_channel_name,
                    is_dm_default = excluded.is_dm_default
            """, (binding_id, team_id, slack_channel_id, slack_channel_name, agent_name,
                  1 if is_dm_default else 0, created_by, now))
            conn.commit()

        return self.get_channel_agent(team_id, slack_channel_id)

    def get_channel_agent(self, team_id: str, slack_channel_id: str) -> Optional[dict]:
        """Get which agent is bound to a channel."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, team_id, slack_channel_id, slack_channel_name, agent_name,
                       is_dm_default, created_by, created_at
                FROM slack_channel_agents
                WHERE team_id = ? AND slack_channel_id = ?
            """, (team_id, slack_channel_id))
            row = cursor.fetchone()

        if not row:
            return None
        return self._row_to_channel_agent(row)

    def get_agent_name_for_channel(self, team_id: str, slack_channel_id: str) -> Optional[str]:
        """Get agent name for a channel (fast lookup)."""
        binding = self.get_channel_agent(team_id, slack_channel_id)
        return binding["agent_name"] if binding else None

    def get_dm_default_agent(self, team_id: str) -> Optional[str]:
        """Get the default agent for DMs in a workspace."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT agent_name FROM slack_channel_agents
                WHERE team_id = ? AND is_dm_default = 1
                LIMIT 1
            """, (team_id,))
            row = cursor.fetchone()
        return row[0] if row else None

    def get_agents_for_workspace(self, team_id: str) -> List[dict]:
        """Get all agent-channel bindings for a workspace."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, team_id, slack_channel_id, slack_channel_name, agent_name,
                       is_dm_default, created_by, created_at
                FROM slack_channel_agents
                WHERE team_id = ?
                ORDER BY created_at ASC
            """, (team_id,))
            rows = cursor.fetchall()

        return [self._row_to_channel_agent(row) for row in rows]

    def get_channel_for_agent(self, team_id: str, agent_name: str) -> Optional[dict]:
        """Get channel binding for a specific agent in a workspace."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, team_id, slack_channel_id, slack_channel_name, agent_name,
                       is_dm_default, created_by, created_at
                FROM slack_channel_agents
                WHERE team_id = ? AND agent_name = ?
            """, (team_id, agent_name))
            row = cursor.fetchone()

        if not row:
            return None
        return self._row_to_channel_agent(row)

    def unbind_agent(self, team_id: str, agent_name: str) -> bool:
        """Remove an agent's channel binding."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM slack_channel_agents
                WHERE team_id = ? AND agent_name = ?
            """, (team_id, agent_name))
            deleted = cursor.rowcount > 0
            conn.commit()
        return deleted

    def unbind_channel(self, team_id: str, slack_channel_id: str) -> bool:
        """Remove a channel's agent binding."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM slack_channel_agents
                WHERE team_id = ? AND slack_channel_id = ?
            """, (team_id, slack_channel_id))
            deleted = cursor.rowcount > 0
            conn.commit()
        return deleted

    # =========================================================================
    # Row converters
    # =========================================================================

    def _row_to_workspace(self, row) -> dict:
        return {
            "id": row[0],
            "team_id": row[1],
            "team_name": row[2],
            "bot_token": row[3],
            "connected_by": row[4],
            "connected_at": row[5],
            "enabled": bool(row[6]),
        }

    # =========================================================================
    # Active Thread Operations (for reply-without-mention)
    # =========================================================================

    def register_active_thread(
        self,
        team_id: str,
        channel_id: str,
        thread_ts: str,
        agent_name: str,
    ) -> None:
        """Record that the bot responded in a thread (enables reply-without-mention)."""
        now = datetime.utcnow().isoformat()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO slack_active_threads
                (team_id, channel_id, thread_ts, agent_name, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (team_id, channel_id, thread_ts, agent_name, now))
            conn.commit()

    def is_active_thread(self, team_id: str, channel_id: str, thread_ts: str) -> Optional[str]:
        """Check if a thread is active (bot participated). Returns agent_name or None."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT agent_name FROM slack_active_threads
                WHERE team_id = ? AND channel_id = ? AND thread_ts = ?
            """, (team_id, channel_id, thread_ts))
            row = cursor.fetchone()
        return row[0] if row else None

    # =========================================================================
    # Row converters
    # =========================================================================

    def _row_to_channel_agent(self, row) -> dict:
        return {
            "id": row[0],
            "team_id": row[1],
            "slack_channel_id": row[2],
            "slack_channel_name": row[3],
            "agent_name": row[4],
            "is_dm_default": bool(row[5]),
            "created_by": row[6],
            "created_at": row[7],
        }
