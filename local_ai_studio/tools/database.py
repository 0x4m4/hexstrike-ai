"""
Database query tools for data analysis.

Currently supports SQLite with configurable result limits.
Designed to be extended with additional database backends.
"""

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Optional

from local_ai_studio.config import StudioConfig
from local_ai_studio.tools.executor import ToolDefinition


def create_sqlite_query_tool(config: StudioConfig) -> ToolDefinition:
    def sqlite_query(database_path: str, query: str, params: Optional[list] = None) -> str:
        db_cfg = config.get("tools.database", {})
        max_rows = db_cfg.get("max_rows", 10000)

        # Resolve path
        db_path = os.path.abspath(os.path.expanduser(database_path))
        if not os.path.exists(db_path):
            return f"[Error] Database not found: {db_path}"

        # Safety: block destructive statements unless explicitly allowed
        upper_query = query.strip().upper()
        if any(upper_query.startswith(kw) for kw in ("DROP", "DELETE", "TRUNCATE", "ALTER")):
            return "[Denied] Destructive SQL statements are not allowed"

        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params or [])

            if upper_query.startswith("SELECT") or upper_query.startswith("WITH") or upper_query.startswith("PRAGMA"):
                rows = cursor.fetchmany(max_rows)
                if not rows:
                    return "(no results)"
                columns = rows[0].keys()
                results = [dict(row) for row in rows]
                output = {
                    "columns": list(columns),
                    "row_count": len(results),
                    "data": results[:100],  # Limit output for readability
                }
                if len(results) > 100:
                    output["note"] = f"Showing 100 of {len(results)} rows"
                return json.dumps(output, indent=2, default=str)
            else:
                conn.commit()
                return f"Query executed. Rows affected: {cursor.rowcount}"
        except sqlite3.Error as e:
            return f"[SQLite Error] {e}"
        except Exception as e:
            return f"[Error] {type(e).__name__}: {e}"
        finally:
            try:
                conn.close()
            except Exception:
                pass

    return ToolDefinition(
        name="sqlite_query",
        description="Execute a SQL query against a SQLite database. Returns results as JSON.",
        parameters={
            "type": "object",
            "properties": {
                "database_path": {
                    "type": "string",
                    "description": "Path to the SQLite database file",
                },
                "query": {"type": "string", "description": "SQL query to execute"},
                "params": {
                    "type": "array",
                    "items": {},
                    "description": "Optional query parameters for parameterized queries",
                },
            },
            "required": ["database_path", "query"],
        },
        handler=sqlite_query,
        category="database",
    )


def create_csv_query_tool(config: StudioConfig) -> ToolDefinition:
    def csv_query(file_path: str, query: str = "") -> str:
        """Load a CSV file and optionally query it using SQL via an in-memory SQLite db."""
        abs_path = os.path.abspath(os.path.expanduser(file_path))
        if not os.path.exists(abs_path):
            return f"[Error] File not found: {abs_path}"

        try:
            import csv as csv_mod
            with open(abs_path, "r", newline="", errors="replace") as f:
                reader = csv_mod.DictReader(f)
                rows = list(reader)

            if not rows:
                return "(empty CSV)"

            if not query:
                # Return schema and preview
                columns = list(rows[0].keys())
                preview = rows[:10]
                return json.dumps({
                    "columns": columns,
                    "total_rows": len(rows),
                    "preview": preview,
                }, indent=2)

            # Load into in-memory SQLite and query
            conn = sqlite3.connect(":memory:")
            columns = list(rows[0].keys())
            safe_cols = [c.replace(" ", "_").replace("-", "_") for c in columns]
            create_sql = f"CREATE TABLE data ({', '.join(f'{c} TEXT' for c in safe_cols)})"
            conn.execute(create_sql)
            insert_sql = f"INSERT INTO data VALUES ({', '.join('?' for _ in safe_cols)})"
            for row in rows:
                conn.execute(insert_sql, [row.get(c, "") for c in columns])
            conn.commit()

            cursor = conn.execute(query)
            result_rows = cursor.fetchall()
            result_cols = [desc[0] for desc in cursor.description] if cursor.description else []
            conn.close()

            results = [dict(zip(result_cols, r)) for r in result_rows[:100]]
            return json.dumps({
                "columns": result_cols,
                "row_count": len(result_rows),
                "data": results,
            }, indent=2, default=str)

        except Exception as e:
            return f"[Error] {type(e).__name__}: {e}"

    return ToolDefinition(
        name="csv_query",
        description="Load a CSV file and optionally query it with SQL. Table name is 'data'.",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the CSV file"},
                "query": {
                    "type": "string",
                    "description": "Optional SQL query (table is named 'data')",
                },
            },
            "required": ["file_path"],
        },
        handler=csv_query,
        category="database",
    )


def register_database_tools(config: StudioConfig, executor) -> None:
    """Register all database tools with the executor."""
    executor.register(create_sqlite_query_tool(config))
    executor.register(create_csv_query_tool(config))
