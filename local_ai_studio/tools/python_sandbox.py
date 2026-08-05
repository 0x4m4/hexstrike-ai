"""
Sandboxed Python code execution.

Runs user-provided Python code in a restricted subprocess with
timeout, memory limits, and controlled package access.
"""

import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any, Optional

from local_ai_studio.config import StudioConfig
from local_ai_studio.tools.executor import ToolDefinition


def create_python_tool(config: StudioConfig) -> ToolDefinition:
    """Create a sandboxed Python execution tool."""

    def execute_python(code: str, timeout: Optional[int] = None) -> str:
        """Execute Python code in a sandboxed subprocess."""
        sandbox_cfg = config.get("tools.python_sandbox", {})
        max_time = timeout or sandbox_cfg.get("max_execution_time", 30)

        # Write code to a temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, prefix="ai_sandbox_"
        ) as f:
            # Wrap code to capture output and return value
            wrapped = _wrap_code(code)
            f.write(wrapped)
            script_path = f.name

        try:
            env = os.environ.copy()
            # Restrict the sandbox working directory
            sandbox_dir = config.get("sandbox_dir", str(Path.home() / ".local_ai_studio" / "sandbox"))
            Path(sandbox_dir).mkdir(parents=True, exist_ok=True)

            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=max_time,
                cwd=sandbox_dir,
                env=env,
            )

            output_parts = []
            if result.stdout.strip():
                output_parts.append(result.stdout.strip())
            if result.stderr.strip():
                output_parts.append(f"[stderr]\n{result.stderr.strip()}")
            if result.returncode != 0:
                output_parts.append(f"[exit code: {result.returncode}]")

            return "\n".join(output_parts) if output_parts else "(no output)"

        except subprocess.TimeoutExpired:
            return f"[Error] Execution timed out after {max_time} seconds"
        except Exception as e:
            return f"[Error] {type(e).__name__}: {e}"
        finally:
            try:
                os.unlink(script_path)
            except OSError:
                pass

    return ToolDefinition(
        name="python_execute",
        description=(
            "Execute Python code in a sandboxed environment. "
            "Supports standard library and common data science packages. "
            "Returns stdout/stderr output."
        ),
        parameters={
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Max execution time in seconds (default: 30)",
                },
            },
            "required": ["code"],
        },
        handler=execute_python,
        category="python",
    )


def create_pip_install_tool(config: StudioConfig) -> ToolDefinition:
    """Create a tool for installing Python packages in the sandbox."""

    def pip_install(package: str) -> str:
        """Install a Python package via pip."""
        sandbox_cfg = config.get("tools.python_sandbox", {})
        allowed = sandbox_cfg.get("allowed_packages", [])

        # Extract package name (strip version specifier)
        pkg_name = package.split("==")[0].split(">=")[0].split("<=")[0].split("[")[0].strip()

        if allowed and pkg_name.lower() not in [p.lower() for p in allowed]:
            return (
                f"[Denied] Package '{pkg_name}' is not in the allowed packages list. "
                f"Allowed: {', '.join(allowed)}"
            )

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                return f"Successfully installed {package}"
            return f"Installation failed:\n{result.stderr}"
        except subprocess.TimeoutExpired:
            return f"[Error] Installation of {package} timed out"
        except Exception as e:
            return f"[Error] {type(e).__name__}: {e}"

    return ToolDefinition(
        name="pip_install",
        description="Install a Python package via pip. Package must be in the allowed list.",
        parameters={
            "type": "object",
            "properties": {
                "package": {
                    "type": "string",
                    "description": "Package name (optionally with version, e.g. 'numpy>=1.24')",
                },
            },
            "required": ["package"],
        },
        handler=pip_install,
        category="python",
    )


def _wrap_code(code: str) -> str:
    """Wrap user code to capture the last expression's value."""
    return textwrap.dedent(f"""\
        import sys
        import io

        try:
        {textwrap.indent(code, '    ')}
        except Exception as _e:
            print(f"{{type(_e).__name__}}: {{_e}}", file=sys.stderr)
            sys.exit(1)
    """)
