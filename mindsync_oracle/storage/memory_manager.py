#!/usr/bin/env python3
"""
MindSync Oracle - Persistent Memory Manager

The brain's long-term memory - stores everything the agent learns about you.
This is THE missing piece that makes AI actually remember and learn.
"""

import sqlite3
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Persistent memory storage for MindSync Oracle.

    What gets stored:
    - User patterns (tool preferences, workflows, blind spots)
    - Goals and tasks (active, completed, paused)
    - Conversation history (full context)
    - Decisions and outcomes (learning from results)
    - Project context (ongoing work)
    """

    def __init__(self, db_path: str = "mindsync_memory.db"):
        """Initialize persistent memory database."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        logger.info(f"Memory Manager initialized: {self.db_path}")

    def _init_database(self):
        """Create database schema if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_type TEXT NOT NULL,
                    pattern_data JSON NOT NULL,
                    confidence REAL DEFAULT 0.5,
                    occurrence_count INTEGER DEFAULT 1,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    goal_text TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    priority TEXT DEFAULT 'medium',
                    sub_tasks JSON,
                    progress REAL DEFAULT 0.0,
                    context JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    input_text TEXT NOT NULL,
                    input_type TEXT DEFAULT 'text',
                    agent_response TEXT,
                    context JSON,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    decision_context TEXT NOT NULL,
                    options JSON,
                    chosen_option TEXT,
                    reasoning TEXT,
                    outcome TEXT,
                    outcome_quality TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_name TEXT NOT NULL,
                    project_type TEXT,
                    description TEXT,
                    metadata JSON,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for common queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_patterns_type
                ON user_patterns(pattern_type)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_goals_status
                ON goals(status)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_timestamp
                ON conversations(timestamp)
            """)

            conn.commit()
            logger.info("Database schema initialized")

    # ===== PATTERN MANAGEMENT =====

    def store_pattern(self, pattern_type: str, pattern_data: Dict[str, Any],
                     confidence: float = 0.5) -> int:
        """
        Store a detected user pattern.

        Args:
            pattern_type: Type of pattern (e.g., 'tool_preference', 'workflow', 'blind_spot')
            pattern_data: The pattern details as a dictionary
            confidence: Confidence score (0.0 to 1.0)

        Returns:
            Pattern ID
        """
        # Check if similar pattern exists
        existing = self.get_patterns(pattern_type)
        for pattern in existing:
            if pattern['pattern_data'] == pattern_data:
                # Update existing pattern
                return self._update_pattern(pattern['id'], confidence)

        # Create new pattern
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO user_patterns (pattern_type, pattern_data, confidence)
                VALUES (?, ?, ?)
            """, (pattern_type, json.dumps(pattern_data), confidence))
            conn.commit()
            pattern_id = cursor.lastrowid
            logger.info(f"Stored new pattern: {pattern_type} (ID: {pattern_id})")
            return pattern_id

    def _update_pattern(self, pattern_id: int, new_confidence: float) -> int:
        """Update existing pattern with increased confidence."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE user_patterns
                SET confidence = (confidence + ?) / 2,
                    occurrence_count = occurrence_count + 1,
                    last_seen = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_confidence, pattern_id))
            conn.commit()
            logger.info(f"Updated pattern {pattern_id} confidence")
            return pattern_id

    def get_patterns(self, pattern_type: Optional[str] = None,
                    min_confidence: float = 0.0) -> List[Dict[str, Any]]:
        """
        Retrieve stored patterns.

        Args:
            pattern_type: Filter by pattern type (None = all types)
            min_confidence: Minimum confidence threshold

        Returns:
            List of patterns
        """
        with sqlite3.connect(self.db_path) as conn:
            if pattern_type:
                cursor = conn.execute("""
                    SELECT id, pattern_type, pattern_data, confidence,
                           occurrence_count, last_seen, created_at
                    FROM user_patterns
                    WHERE pattern_type = ? AND confidence >= ?
                    ORDER BY confidence DESC, occurrence_count DESC
                """, (pattern_type, min_confidence))
            else:
                cursor = conn.execute("""
                    SELECT id, pattern_type, pattern_data, confidence,
                           occurrence_count, last_seen, created_at
                    FROM user_patterns
                    WHERE confidence >= ?
                    ORDER BY confidence DESC, occurrence_count DESC
                """, (min_confidence,))

            patterns = []
            for row in cursor.fetchall():
                patterns.append({
                    'id': row[0],
                    'pattern_type': row[1],
                    'pattern_data': json.loads(row[2]),
                    'confidence': row[3],
                    'occurrence_count': row[4],
                    'last_seen': row[5],
                    'created_at': row[6]
                })
            return patterns

    # ===== GOAL MANAGEMENT =====

    def create_goal(self, goal_text: str, priority: str = "medium",
                   sub_tasks: Optional[List[str]] = None,
                   context: Optional[Dict[str, Any]] = None) -> int:
        """
        Create a new goal for autonomous pursuit.

        Args:
            goal_text: Natural language description of the goal
            priority: 'low', 'medium', 'high', 'critical'
            sub_tasks: Optional list of sub-tasks
            context: Optional additional context

        Returns:
            Goal ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO goals (goal_text, priority, sub_tasks, context)
                VALUES (?, ?, ?, ?)
            """, (goal_text, priority,
                  json.dumps(sub_tasks or []),
                  json.dumps(context or {})))
            conn.commit()
            goal_id = cursor.lastrowid
            logger.info(f"Created goal: '{goal_text}' (ID: {goal_id})")
            return goal_id

    def update_goal_progress(self, goal_id: int, progress: float,
                            status: Optional[str] = None):
        """
        Update goal progress and optionally change status.

        Args:
            goal_id: Goal ID
            progress: Progress percentage (0.0 to 1.0)
            status: New status ('active', 'completed', 'paused', 'failed')
        """
        with sqlite3.connect(self.db_path) as conn:
            if status:
                completed_at = datetime.now() if status == 'completed' else None
                conn.execute("""
                    UPDATE goals
                    SET progress = ?, status = ?, updated_at = CURRENT_TIMESTAMP,
                        completed_at = ?
                    WHERE id = ?
                """, (progress, status, completed_at, goal_id))
            else:
                conn.execute("""
                    UPDATE goals
                    SET progress = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (progress, goal_id))
            conn.commit()
            logger.info(f"Updated goal {goal_id}: progress={progress}, status={status}")

    def get_active_goals(self) -> List[Dict[str, Any]]:
        """Get all active goals for autonomous processing."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, goal_text, priority, sub_tasks, progress, context,
                       created_at, updated_at
                FROM goals
                WHERE status = 'active'
                ORDER BY
                    CASE priority
                        WHEN 'critical' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'medium' THEN 3
                        WHEN 'low' THEN 4
                    END,
                    created_at ASC
            """)

            goals = []
            for row in cursor.fetchall():
                goals.append({
                    'id': row[0],
                    'goal_text': row[1],
                    'priority': row[2],
                    'sub_tasks': json.loads(row[3]),
                    'progress': row[4],
                    'context': json.loads(row[5]),
                    'created_at': row[6],
                    'updated_at': row[7]
                })
            return goals

    # ===== CONVERSATION MANAGEMENT =====

    def store_conversation(self, input_text: str, agent_response: str,
                          input_type: str = "text",
                          context: Optional[Dict[str, Any]] = None) -> int:
        """Store conversation for context building."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO conversations (input_text, input_type, agent_response, context)
                VALUES (?, ?, ?, ?)
            """, (input_text, input_type, agent_response, json.dumps(context or {})))
            conn.commit()
            return cursor.lastrowid

    def get_recent_conversations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversations for context."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, input_text, input_type, agent_response, context, timestamp
                FROM conversations
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

            conversations = []
            for row in cursor.fetchall():
                conversations.append({
                    'id': row[0],
                    'input_text': row[1],
                    'input_type': row[2],
                    'agent_response': row[3],
                    'context': json.loads(row[4]),
                    'timestamp': row[5]
                })
            return conversations

    # ===== DECISION TRACKING =====

    def store_decision(self, decision_context: str, options: List[str],
                      chosen_option: str, reasoning: str) -> int:
        """Store a decision for learning from outcomes."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO decisions (decision_context, options, chosen_option, reasoning)
                VALUES (?, ?, ?, ?)
            """, (decision_context, json.dumps(options), chosen_option, reasoning))
            conn.commit()
            return cursor.lastrowid

    def update_decision_outcome(self, decision_id: int, outcome: str,
                               outcome_quality: str):
        """
        Update decision with outcome for learning.

        Args:
            decision_id: Decision ID
            outcome: Description of what happened
            outcome_quality: 'good', 'bad', 'neutral'
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE decisions
                SET outcome = ?, outcome_quality = ?
                WHERE id = ?
            """, (outcome, outcome_quality, decision_id))
            conn.commit()
            logger.info(f"Decision {decision_id} outcome: {outcome_quality}")

    # ===== PROJECT MANAGEMENT =====

    def create_project(self, project_name: str, project_type: str,
                      description: str = "",
                      metadata: Optional[Dict[str, Any]] = None) -> int:
        """Create a new project context."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO projects (project_name, project_type, description, metadata)
                VALUES (?, ?, ?, ?)
            """, (project_name, project_type, description, json.dumps(metadata or {})))
            conn.commit()
            project_id = cursor.lastrowid
            logger.info(f"Created project: {project_name} (ID: {project_id})")
            return project_id

    def get_active_projects(self) -> List[Dict[str, Any]]:
        """Get all active projects."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, project_name, project_type, description, metadata,
                       created_at, updated_at
                FROM projects
                WHERE status = 'active'
                ORDER BY updated_at DESC
            """)

            projects = []
            for row in cursor.fetchall():
                projects.append({
                    'id': row[0],
                    'project_name': row[1],
                    'project_type': row[2],
                    'description': row[3],
                    'metadata': json.loads(row[4]),
                    'created_at': row[5],
                    'updated_at': row[6]
                })
            return projects

    # ===== UTILITY METHODS =====

    def get_context_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive context summary for agent.
        This is what makes the AI "remember" you.
        """
        return {
            'patterns': self.get_patterns(min_confidence=0.6),
            'active_goals': self.get_active_goals(),
            'recent_conversations': self.get_recent_conversations(limit=5),
            'active_projects': self.get_active_projects(),
            'statistics': {
                'total_patterns': self._count_table('user_patterns'),
                'total_goals': self._count_table('goals'),
                'completed_goals': self._count_completed_goals(),
                'total_conversations': self._count_table('conversations'),
            }
        }

    def _count_table(self, table_name: str) -> int:
        """Count rows in a table."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            return cursor.fetchone()[0]

    def _count_completed_goals(self) -> int:
        """Count completed goals."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM goals WHERE status = 'completed'")
            return cursor.fetchone()[0]


if __name__ == "__main__":
    # Test the memory manager
    logging.basicConfig(level=logging.INFO)

    memory = MemoryManager("test_memory.db")

    # Store a pattern
    pattern_id = memory.store_pattern(
        "tool_preference",
        {"tool": "nmap", "args": "-sV -sC", "reason": "user always uses these flags"},
        confidence=0.8
    )
    print(f"Stored pattern: {pattern_id}")

    # Create a goal
    goal_id = memory.create_goal(
        "Research CVE-2024-1234 and prepare exploit analysis",
        priority="high",
        sub_tasks=["Find CVE details", "Locate exploit code", "Test on lab environment"]
    )
    print(f"Created goal: {goal_id}")

    # Get context summary
    context = memory.get_context_summary()
    print(f"\nContext Summary:\n{json.dumps(context, indent=2)}")
