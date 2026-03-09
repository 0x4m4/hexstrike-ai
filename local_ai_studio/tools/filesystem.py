"""
File system tools with configurable root restrictions.

Provides read, write, list, search, and info operations within
allowed directories only.
"""

import os
import shutil
from pathlib import Path
from typing import Optional

from local_ai_studio.config import StudioConfig
from local_ai_studio.tools.executor import ToolDefinition


def _resolve_and_check(path: str, config: StudioConfig) -> str:
    """Resolve path and check it falls within allowed roots.

    Returns the absolute path string or raises PermissionError.
    """
    fs_cfg = config.get("tools.filesystem", {})
    allowed_roots = fs_cfg.get("allowed_roots", [])
    resolved = os.path.abspath(os.path.expanduser(path))

    if not allowed_roots:
        # If no roots configured, restrict to sandbox
        sandbox = config.get("sandbox_dir", str(Path.home() / ".local_ai_studio" / "sandbox"))
        allowed_roots = [sandbox]

    for root in allowed_roots:
        abs_root = os.path.abspath(os.path.expanduser(root))
        if resolved.startswith(abs_root):
            return resolved

    raise PermissionError(
        f"Path '{resolved}' is outside allowed directories: {allowed_roots}"
    )


def create_file_read_tool(config: StudioConfig) -> ToolDefinition:
    def read_file(path: str, max_lines: int = 500) -> str:
        resolved = _resolve_and_check(path, config)
        if not os.path.isfile(resolved):
            return f"[Error] Not a file: {resolved}"
        try:
            with open(resolved, "r", errors="replace") as f:
                lines = f.readlines()
            if len(lines) > max_lines:
                return (
                    "".join(lines[:max_lines])
                    + f"\n... [truncated, {len(lines) - max_lines} more lines]"
                )
            return "".join(lines)
        except Exception as e:
            return f"[Error] {type(e).__name__}: {e}"

    return ToolDefinition(
        name="file_read",
        description="Read the contents of a file within allowed directories.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file"},
                "max_lines": {
                    "type": "integer",
                    "description": "Maximum lines to return (default 500)",
                },
            },
            "required": ["path"],
        },
        handler=read_file,
        category="filesystem",
    )


def create_file_write_tool(config: StudioConfig) -> ToolDefinition:
    def write_file(path: str, content: str, append: bool = False) -> str:
        fs_cfg = config.get("tools.filesystem", {})
        if not fs_cfg.get("allow_write", True):
            return "[Denied] File write is disabled in configuration"
        resolved = _resolve_and_check(path, config)
        try:
            Path(resolved).parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if append else "w"
            with open(resolved, mode) as f:
                f.write(content)
            return f"Written {len(content)} chars to {resolved}"
        except Exception as e:
            return f"[Error] {type(e).__name__}: {e}"

    return ToolDefinition(
        name="file_write",
        description="Write content to a file. Creates parent directories if needed.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to write to"},
                "content": {"type": "string", "description": "Content to write"},
                "append": {
                    "type": "boolean",
                    "description": "Append instead of overwrite (default false)",
                },
            },
            "required": ["path", "content"],
        },
        handler=write_file,
        category="filesystem",
    )


def create_list_dir_tool(config: StudioConfig) -> ToolDefinition:
    def list_directory(path: str, recursive: bool = False) -> str:
        resolved = _resolve_and_check(path, config)
        if not os.path.isdir(resolved):
            return f"[Error] Not a directory: {resolved}"
        try:
            if recursive:
                entries = []
                for root, dirs, files in os.walk(resolved):
                    rel = os.path.relpath(root, resolved)
                    for f in files:
                        entries.append(os.path.join(rel, f) if rel != "." else f)
                    if len(entries) > 1000:
                        entries.append("... [truncated at 1000 entries]")
                        break
            else:
                entries = sorted(os.listdir(resolved))
                entries = [
                    f"{e}/" if os.path.isdir(os.path.join(resolved, e)) else e
                    for e in entries
                ]
            return "\n".join(entries) if entries else "(empty directory)"
        except Exception as e:
            return f"[Error] {type(e).__name__}: {e}"

    return ToolDefinition(
        name="list_directory",
        description="List files and subdirectories in a directory.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path"},
                "recursive": {
                    "type": "boolean",
                    "description": "List recursively (default false)",
                },
            },
            "required": ["path"],
        },
        handler=list_directory,
        category="filesystem",
    )


def create_file_info_tool(config: StudioConfig) -> ToolDefinition:
    def file_info(path: str) -> str:
        resolved = _resolve_and_check(path, config)
        if not os.path.exists(resolved):
            return f"[Error] Path does not exist: {resolved}"
        try:
            stat = os.stat(resolved)
            return (
                f"Path: {resolved}\n"
                f"Type: {'directory' if os.path.isdir(resolved) else 'file'}\n"
                f"Size: {stat.st_size} bytes\n"
                f"Modified: {stat.st_mtime}\n"
                f"Permissions: {oct(stat.st_mode)}"
            )
        except Exception as e:
            return f"[Error] {type(e).__name__}: {e}"

    return ToolDefinition(
        name="file_info",
        description="Get metadata about a file or directory.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to inspect"},
            },
            "required": ["path"],
        },
        handler=file_info,
        category="filesystem",
    )


def create_file_search_tool(config: StudioConfig) -> ToolDefinition:
    def search_files(directory: str, pattern: str, content_search: str = "") -> str:
        resolved = _resolve_and_check(directory, config)
        if not os.path.isdir(resolved):
            return f"[Error] Not a directory: {resolved}"
        try:
            import fnmatch
            matches = []
            for root, dirs, files in os.walk(resolved):
                for f in files:
                    if fnmatch.fnmatch(f, pattern):
                        full = os.path.join(root, f)
                        rel = os.path.relpath(full, resolved)
                        if content_search:
                            try:
                                with open(full, "r", errors="replace") as fh:
                                    text = fh.read()
                                if content_search.lower() in text.lower():
                                    matches.append(rel)
                            except (OSError, UnicodeDecodeError):
                                pass
                        else:
                            matches.append(rel)
                    if len(matches) >= 200:
                        break
            return "\n".join(matches) if matches else "(no matches)"
        except Exception as e:
            return f"[Error] {type(e).__name__}: {e}"

    return ToolDefinition(
        name="file_search",
        description="Search for files by name pattern, optionally filtering by content.",
        parameters={
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Root directory to search"},
                "pattern": {"type": "string", "description": "Filename glob pattern (e.g. '*.py')"},
                "content_search": {
                    "type": "string",
                    "description": "Optional string to search for within matching files",
                },
            },
            "required": ["directory", "pattern"],
        },
        handler=search_files,
        category="filesystem",
    )


def register_filesystem_tools(config: StudioConfig, executor) -> None:
    """Register all filesystem tools with the executor."""
    executor.register(create_file_read_tool(config))
    executor.register(create_file_write_tool(config))
    executor.register(create_list_dir_tool(config))
    executor.register(create_file_info_tool(config))
    executor.register(create_file_search_tool(config))
