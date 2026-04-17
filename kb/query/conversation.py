"""Multi-turn conversation session management for RAG."""

import json
import logging
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict

from kb.query.models import ConversationTurn, ConversationSession

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages multi-turn RAG conversation sessions persisted in SQLite."""
    
    def __init__(self, db_path: str):
        """Initialize with path to conversations database file.
        
        Args:
            db_path: Path to the conversations.db file
        """
        self.db_path = Path(db_path)
        # Ensure the directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_tables()
    
    @contextmanager
    def _connect(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        # Enable foreign keys and WAL mode
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        try:
            yield conn
        finally:
            conn.close()
    
    def _ensure_tables(self):
        """Create conversation tables if they don't exist."""
        with self._connect() as conn:
            cursor = conn.cursor()
            
            # Create sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rag_conversations (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                )
            """)
            
            # Create turns table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rag_conversation_turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sources TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (session_id) REFERENCES rag_conversations(session_id) ON DELETE CASCADE
                )
            """)
            
            # Create index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversation_turns_session 
                ON rag_conversation_turns(session_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversation_turns_created 
                ON rag_conversation_turns(created_at)
            """)
            
            conn.commit()
            logger.debug("Conversation tables ensured")
    
    def create_session(self) -> str:
        """Create a new conversation session. Returns session_id (UUID)."""
        session_id = str(uuid.uuid4())
        
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO rag_conversations (session_id, created_at, updated_at)
                VALUES (?, datetime('now'), datetime('now'))
            """, (session_id,))
            conn.commit()
        
        logger.debug(f"Created conversation session: {session_id}")
        return session_id
    
    def add_turn(self, session_id: str, role: str, content: str, 
                 sources: Optional[List[Dict]] = None) -> None:
        """Add a turn to an existing session.
        
        Args:
            session_id: The conversation session ID
            role: Either 'user' or 'assistant'
            content: The message content
            sources: Optional list of source dicts (with id, metadata, score, content)
                     or legacy list of source IDs (strings) for backward compatibility
        """
        if role not in ('user', 'assistant'):
            raise ValueError(f"Invalid role: {role}. Must be 'user' or 'assistant'")
        
        sources_json = json.dumps(sources) if sources else None
        
        with self._connect() as conn:
            cursor = conn.cursor()
            
            # Insert the turn
            cursor.execute("""
                INSERT INTO rag_conversation_turns (session_id, role, content, sources, created_at)
                VALUES (?, ?, ?, ?, datetime('now'))
            """, (session_id, role, content, sources_json))
            
            # Update session's updated_at timestamp
            cursor.execute("""
                UPDATE rag_conversations 
                SET updated_at = datetime('now')
                WHERE session_id = ?
            """, (session_id,))
            
            conn.commit()
        
        logger.debug(f"Added turn to session {session_id}: {role}")
    
    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Get full conversation session with all turns.
        
        Args:
            session_id: The conversation session ID
            
        Returns:
            ConversationSession with all turns, or None if not found
        """
        with self._connect() as conn:
            cursor = conn.cursor()
            
            # Get session info
            cursor.execute("""
                SELECT session_id, created_at, updated_at 
                FROM rag_conversations 
                WHERE session_id = ?
            """, (session_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            session_id_val = row['session_id']
            created_at = row['created_at']
            updated_at = row['updated_at']
            
            # Get all turns
            cursor.execute("""
                SELECT role, content, sources, created_at
                FROM rag_conversation_turns
                WHERE session_id = ?
                ORDER BY created_at ASC, id ASC
            """, (session_id,))
            
            turns = []
            for turn_row in cursor.fetchall():
                sources = None
                if turn_row['sources']:
                    try:
                        sources = json.loads(turn_row['sources'])
                    except json.JSONDecodeError:
                        pass
                
                turn = ConversationTurn(
                    role=turn_row['role'],
                    content=turn_row['content'],
                    sources=sources,
                    timestamp=turn_row['created_at']
                )
                turns.append(turn)
            
            return ConversationSession(
                session_id=session_id_val,
                turns=turns,
                created_at=created_at,
                updated_at=updated_at
            )
    
    def get_recent_turns(self, session_id: str, limit: int = 5) -> List[ConversationTurn]:
        """Get the most recent N turns for context injection.
        
        Args:
            session_id: The conversation session ID
            limit: Maximum number of turns to return
            
        Returns:
            List of recent conversation turns (oldest first)
        """
        with self._connect() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT role, content, sources, created_at
                FROM rag_conversation_turns
                WHERE session_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
            """, (session_id, limit))
            
            turns = []
            for row in cursor.fetchall():
                sources = None
                if row['sources']:
                    try:
                        sources = json.loads(row['sources'])
                    except json.JSONDecodeError:
                        pass
                
                turn = ConversationTurn(
                    role=row['role'],
                    content=row['content'],
                    sources=sources,
                    timestamp=row['created_at']
                )
                turns.append(turn)
            
            # Reverse to get oldest first
            turns.reverse()
            return turns
    
    def list_sessions(self, limit: int = 20) -> List[Dict]:
        """List conversation sessions with summary info.
        
        Returns:
            List of dicts with session_id, created_at, turn_count, last_question
        """
        with self._connect() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    c.session_id,
                    c.created_at,
                    c.updated_at,
                    COUNT(t.id) as turn_count
                FROM rag_conversations c
                LEFT JOIN rag_conversation_turns t ON c.session_id = t.session_id
                GROUP BY c.session_id
                ORDER BY c.updated_at DESC
                LIMIT ?
            """, (limit,))
            
            sessions = []
            for row in cursor.fetchall():
                session_id = row['session_id']
                
                # Get the first user turn as "last_question" (most recent question)
                cursor.execute("""
                    SELECT content
                    FROM rag_conversation_turns
                    WHERE session_id = ? AND role = 'user'
                    ORDER BY created_at DESC, id DESC
                    LIMIT 1
                """, (session_id,))
                
                last_question_row = cursor.fetchone()
                last_question = last_question_row['content'] if last_question_row else None
                
                sessions.append({
                    'session_id': session_id,
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'turn_count': row['turn_count'],
                    'last_question': last_question
                })
            
            return sessions
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a conversation session and all its turns.
        
        Args:
            session_id: The conversation session ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        with self._connect() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM rag_conversations WHERE session_id = ?
            """, (session_id,))
            
            deleted = cursor.rowcount > 0
            conn.commit()
        
        if deleted:
            logger.debug(f"Deleted conversation session: {session_id}")
        return deleted
    
    def cleanup_expired(self, timeout_minutes: int = 30) -> int:
        """Delete sessions that have been inactive for longer than timeout.
        
        Args:
            timeout_minutes: Inactivity timeout in minutes
            
        Returns:
            Number of sessions deleted
        """
        with self._connect() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM rag_conversations
                WHERE updated_at < datetime('now', '-{} minutes')
            """.format(timeout_minutes))
            
            deleted_count = cursor.rowcount
            conn.commit()
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} expired conversation sessions")
        return deleted_count
    
    def cleanup_all(self) -> int:
        """Delete all conversation sessions and vacuum the database.
        
        Returns:
            Number of sessions deleted
        """
        with self._connect() as conn:
            cursor = conn.cursor()
            
            # Count sessions before deletion
            cursor.execute("SELECT COUNT(*) FROM rag_conversations")
            count = cursor.fetchone()[0]
            
            # Delete all sessions (cascade deletes turns via foreign key)
            cursor.execute("DELETE FROM rag_conversations")
            conn.commit()
            
            # Vacuum to reclaim space
            cursor.execute("VACUUM")
            conn.commit()
        
        logger.info(f"Cleaned up all {count} conversation sessions")
        return count
    
    def format_history_for_prompt(self, session_id: str, max_turns: int = 5) -> str:
        """Format recent conversation turns as text for LLM prompt injection.
        
        Returns string like:
        User: What is Python?
        Assistant: Python is a programming language...
        User: What about its type system?
        
        Args:
            session_id: The conversation session ID
            max_turns: Maximum number of turns to include
            
        Returns:
            Formatted conversation history string (empty if no history)
        """
        turns = self.get_recent_turns(session_id, limit=max_turns)
        
        if not turns:
            return ""
        
        # Estimate tokens (rough approximation: 4 chars per token)
        MAX_HISTORY_CHARS = 4000  # ~1000 tokens
        
        formatted_parts = []
        current_length = 0
        
        for turn in turns:
            role_label = "User" if turn.role == "user" else "Assistant"
            turn_text = f"{role_label}: {turn.content}\n\n"
            
            # Check if adding this turn would exceed the limit
            if current_length + len(turn_text) > MAX_HISTORY_CHARS:
                # Truncate the last turn if needed
                remaining = MAX_HISTORY_CHARS - current_length
                if remaining > 50:  # Only add if we have meaningful space
                    truncated = turn_text[:remaining - 3] + "..."
                    formatted_parts.append(truncated)
                break
            
            formatted_parts.append(turn_text)
            current_length += len(turn_text)
        
        return "".join(formatted_parts).strip()
