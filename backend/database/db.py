import sqlite3
import os

DB_PATH = "assistant.db"


def init_db():
    """Initialize the SQLite database structure."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Conversation history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Persistent agent task history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id TEXT NOT NULL UNIQUE,
            original_request TEXT NOT NULL,
            intent TEXT,
            state TEXT NOT NULL,
            planner_source TEXT,
            final_result TEXT,
            error TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME
        )
    """)

    # Individual tasks belonging to a plan
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_history_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id TEXT NOT NULL,
            task_id INTEGER NOT NULL,
            description TEXT,
            tool_name TEXT,
            tool_args TEXT,
            status TEXT NOT NULL,
            result TEXT,
            error TEXT,
            requires_approval INTEGER DEFAULT 0,
            FOREIGN KEY (plan_id) REFERENCES task_history(plan_id)
        )
    """)

    conn.commit()
    conn.close()


def get_connection():
    """Return a SQLite database connection."""
    return sqlite3.connect(DB_PATH)

import json
from datetime import datetime


def save_task_history(plan):
    """Persist a completed agent plan and its tasks."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        completed_at = None
        if plan.state.value in {"COMPLETED", "FAILED"}:
            completed_at = datetime.now().isoformat()

        cursor.execute("""
            INSERT OR REPLACE INTO task_history
            (plan_id, original_request, intent, state, planner_source,
             final_result, error, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            plan.id,
            plan.original_request,
            plan.intent,
            plan.state.value,
            plan.planner_source,
            plan.final_result,
            plan.error,
            completed_at
        ))

        cursor.execute(
            "DELETE FROM task_history_items WHERE plan_id = ?",
            (plan.id,)
        )

        for task in plan.tasks:
            cursor.execute("""
                INSERT INTO task_history_items
                (plan_id, task_id, description, tool_name, tool_args,
                 status, result, error, requires_approval)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                plan.id,
                task.id,
                task.description,
                task.tool_name,
                json.dumps(task.tool_args, default=str),
                task.status.value,
                json.dumps(task.result, default=str),
                task.error,
                1 if task.requires_approval else 0
            ))

        conn.commit()

    finally:
        conn.close()


def get_task_history(limit=50):
    """Return recent task history."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT plan_id, original_request, intent, state,
                   planner_source, final_result, error,
                   created_at, completed_at
            FROM task_history
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()

        return [
            {
                "plan_id": row[0],
                "original_request": row[1],
                "intent": row[2],
                "state": row[3],
                "planner_source": row[4],
                "final_result": row[5],
                "error": row[6],
                "created_at": row[7],
                "completed_at": row[8]
            }
            for row in rows
        ]

    finally:
        conn.close()


def get_task_history_by_plan_id(plan_id):
    """Return one saved plan and its individual tasks."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT plan_id, original_request, intent, state,
                   planner_source, final_result, error,
                   created_at, completed_at
            FROM task_history
            WHERE plan_id = ?
        """, (plan_id,))

        plan_row = cursor.fetchone()

        if not plan_row:
            return None

        cursor.execute("""
            SELECT task_id, description, tool_name, tool_args,
                   status, result, error, requires_approval
            FROM task_history_items
            WHERE plan_id = ?
            ORDER BY task_id
        """, (plan_id,))

        task_rows = cursor.fetchall()

        return {
            "plan_id": plan_row[0],
            "original_request": plan_row[1],
            "intent": plan_row[2],
            "state": plan_row[3],
            "planner_source": plan_row[4],
            "final_result": plan_row[5],
            "error": plan_row[6],
            "created_at": plan_row[7],
            "completed_at": plan_row[8],
            "tasks": [
                {
                    "task_id": row[0],
                    "description": row[1],
                    "tool_name": row[2],
                    "tool_args": row[3],
                    "status": row[4],
                    "result": row[5],
                    "error": row[6],
                    "requires_approval": bool(row[7])
                }
                for row in task_rows
            ]
        }

    finally:
        conn.close()