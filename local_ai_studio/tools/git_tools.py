"""
Git operations tool for version control within development projects.

Supports common git operations with safety controls to prevent
destructive actions.
"""

import os
import subprocess
from typing import Optional

from local_ai_studio.config import StudioConfig
from local_ai_studio.tools.executor import ToolDefinition


def _run_git(args: list[str], cwd: str, timeout: int = 30) -> tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except FileNotFoundError:
        return -1, "", "git is not installed"


def create_git_tool(config: StudioConfig) -> ToolDefinition:
    def git_operation(
        operation: str,
        repo_path: str,
        args: Optional[str] = None,
    ) -> str:
        git_cfg = config.get("tools.git", {})
        allowed_ops = git_cfg.get("allowed_operations", [
            "status", "log", "diff", "add", "commit",
            "branch", "checkout", "pull", "push", "stash",
        ])

        op_lower = operation.lower().strip()
        if op_lower not in allowed_ops:
            return f"[Denied] Git operation '{op_lower}' is not allowed. Allowed: {', '.join(allowed_ops)}"

        repo = os.path.abspath(os.path.expanduser(repo_path))
        if not os.path.isdir(os.path.join(repo, ".git")):
            return f"[Error] Not a git repository: {repo}"

        cmd = [op_lower]
        if args:
            cmd.extend(args.split())

        # Safety check for destructive operations
        full_cmd = " ".join(cmd)
        dangerous = ["--force", "-f", "--hard", "push --force", "reset --hard"]
        if any(d in full_cmd for d in dangerous):
            return f"[Denied] Potentially destructive operation blocked: git {full_cmd}"

        code, stdout, stderr = _run_git(cmd, repo)
        if code != 0:
            return f"[Error] git {full_cmd} failed:\n{stderr}"

        output = stdout
        if stderr and code == 0:
            output += f"\n{stderr}" if output else stderr

        return output if output else "(no output)"

    return ToolDefinition(
        name="git",
        description=(
            "Execute git operations on a repository. Supports: status, log, diff, "
            "add, commit, branch, checkout, pull, push, stash."
        ),
        parameters={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "Git operation (status, log, diff, add, commit, etc.)",
                },
                "repo_path": {
                    "type": "string",
                    "description": "Path to the git repository",
                },
                "args": {
                    "type": "string",
                    "description": "Additional arguments (e.g., '-m \"commit message\"' for commit)",
                },
            },
            "required": ["operation", "repo_path"],
        },
        handler=git_operation,
        category="git",
    )


def register_git_tools(config: StudioConfig, executor) -> None:
    """Register git tools with the executor."""
    executor.register(create_git_tool(config))
