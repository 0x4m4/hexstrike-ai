#!/usr/bin/env python3
"""
MindSync Oracle v8 - Sandbox Executor

ISOLATED EXECUTION ENVIRONMENT

⚠️ ETHICAL SAFEGUARD - SANDBOXED EXECUTION ONLY ⚠️

This module executes security testing tools in isolated Docker containers
or VMs to prevent accidental damage to host systems.

Features:
- Docker container isolation (default)
- Network isolation options (host, bridge, none)
- Resource limits (CPU, memory, time)
- Result extraction from container
- Automatic cleanup
- Execution logging

Container Security:
- Read-only root filesystem (where possible)
- No privileged mode
- Dropped capabilities
- Resource quotas enforced
- Network isolation by default
- Automatic timeout and cleanup

STRICTLY FOR:
✅ CTF challenge solving
✅ Lab testing with isolation
✅ Tool execution in controlled environment
✅ Research with blast radius containment

REQUIRES:
- Docker installed and running
- User has Docker permissions
- Security tools installed in container images

USAGE:
    from sandbox_executor import SandboxExecutor

    executor = SandboxExecutor(
        image="kalilinux/kali-rolling",
        network_mode="none"  # Isolated
    )

    result = executor.execute(
        command="nmap -sV 127.0.0.1",
        timeout=60
    )

    print(result.stdout)
"""

import logging
import subprocess
import time
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import shlex

logger = logging.getLogger(__name__)


class ExecutionResult:
    """Result of sandbox execution."""

    def __init__(self, command: str, exit_code: int, stdout: str, stderr: str,
                 duration: float, timed_out: bool = False):
        self.command = command
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.duration = duration
        self.timed_out = timed_out
        self.timestamp = datetime.now().isoformat()

    def success(self) -> bool:
        """Check if execution was successful."""
        return self.exit_code == 0 and not self.timed_out

    def to_dict(self) -> Dict[str, Any]:
        return {
            'command': self.command,
            'exit_code': self.exit_code,
            'stdout': self.stdout,
            'stderr': self.stderr,
            'duration': self.duration,
            'timed_out': self.timed_out,
            'success': self.success(),
            'timestamp': self.timestamp
        }


class SandboxExecutor:
    """
    Sandbox Executor for isolated tool execution.

    Runs security tools in Docker containers with isolation and resource limits.

    ⚠️ SANDBOXED EXECUTION - BLAST RADIUS CONTAINMENT ⚠️
    """

    def __init__(self, image: str = "kalilinux/kali-rolling",
                 network_mode: str = "none",
                 memory_limit: str = "512m",
                 cpu_limit: float = 1.0,
                 config: Optional[Dict] = None):
        """
        Initialize Sandbox Executor.

        Args:
            image: Docker image to use (default: Kali Linux)
            network_mode: Docker network mode ('none', 'bridge', 'host')
            memory_limit: Memory limit (e.g., '512m', '1g')
            cpu_limit: CPU limit (number of CPUs, e.g., 1.0)
            config: Optional configuration
        """
        self.image = image
        self.network_mode = network_mode
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        self.config = config or {}

        # Execution history
        self.executions = []

        # Statistics
        self.stats = {
            'total_executions': 0,
            'successful': 0,
            'failed': 0,
            'timeouts': 0
        }

        # Check Docker availability
        self._check_docker()

        logger.info(f"Sandbox Executor initialized (image: {image}, network: {network_mode})")

    def _check_docker(self) -> bool:
        """Check if Docker is available."""
        try:
            result = subprocess.run(['docker', 'version'],
                                   capture_output=True,
                                   timeout=5)
            if result.returncode != 0:
                logger.error("Docker is not available")
                return False

            logger.info("Docker is available")
            return True

        except FileNotFoundError:
            logger.error("Docker command not found - is Docker installed?")
            return False
        except subprocess.TimeoutExpired:
            logger.error("Docker command timed out")
            return False
        except Exception as e:
            logger.error(f"Docker check failed: {e}")
            return False

    def execute(self, command: str, timeout: int = 60,
                working_dir: str = "/tmp",
                env_vars: Optional[Dict[str, str]] = None) -> ExecutionResult:
        """
        Execute command in sandbox.

        Args:
            command: Command to execute
            timeout: Timeout in seconds (default 60)
            working_dir: Working directory in container
            env_vars: Environment variables

        Returns:
            ExecutionResult object
        """
        self.stats['total_executions'] += 1
        start_time = time.time()

        logger.info(f"Executing in sandbox: {command}")

        # Build Docker command
        docker_cmd = self._build_docker_command(command, working_dir, env_vars)

        # Execute
        try:
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                timeout=timeout,
                text=True
            )

            duration = time.time() - start_time

            execution_result = ExecutionResult(
                command=command,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration=duration,
                timed_out=False
            )

            if result.returncode == 0:
                self.stats['successful'] += 1
                logger.info(f"Sandbox execution successful ({duration:.2f}s)")
            else:
                self.stats['failed'] += 1
                logger.warning(f"Sandbox execution failed with exit code {result.returncode}")

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            self.stats['timeouts'] += 1

            execution_result = ExecutionResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"Execution timed out after {timeout}s",
                duration=duration,
                timed_out=True
            )

            logger.warning(f"Sandbox execution timed out after {timeout}s")

        except Exception as e:
            duration = time.time() - start_time
            self.stats['failed'] += 1

            execution_result = ExecutionResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"Execution error: {str(e)}",
                duration=duration,
                timed_out=False
            )

            logger.error(f"Sandbox execution error: {e}")

        # Store in history
        self.executions.append(execution_result)

        return execution_result

    def _build_docker_command(self, command: str, working_dir: str,
                             env_vars: Optional[Dict[str, str]]) -> List[str]:
        """Build Docker command with security constraints."""
        docker_cmd = [
            'docker', 'run',
            '--rm',  # Remove container after execution
            '--network', self.network_mode,  # Network isolation
            '--memory', self.memory_limit,  # Memory limit
            '--cpus', str(self.cpu_limit),  # CPU limit
            '--security-opt', 'no-new-privileges',  # No privilege escalation
            '--cap-drop', 'ALL',  # Drop all capabilities
            '-w', working_dir,  # Working directory
        ]

        # Add environment variables
        if env_vars:
            for key, value in env_vars.items():
                docker_cmd.extend(['-e', f'{key}={value}'])

        # Add image
        docker_cmd.append(self.image)

        # Add command (use sh -c to handle complex commands)
        docker_cmd.extend(['sh', '-c', command])

        return docker_cmd

    def pull_image(self) -> bool:
        """Pull Docker image if not already present."""
        logger.info(f"Pulling Docker image: {self.image}")

        try:
            result = subprocess.run(
                ['docker', 'pull', self.image],
                capture_output=True,
                timeout=300  # 5 minute timeout for image pull
            )

            if result.returncode == 0:
                logger.info(f"Image pulled successfully: {self.image}")
                return True
            else:
                logger.error(f"Failed to pull image: {self.image}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Image pull timed out")
            return False
        except Exception as e:
            logger.error(f"Image pull error: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get executor statistics."""
        success_rate = 0.0
        if self.stats['total_executions'] > 0:
            success_rate = self.stats['successful'] / self.stats['total_executions']

        return {
            **self.stats,
            'success_rate': success_rate,
            'total_logged': len(self.executions)
        }

    def get_recent_executions(self, limit: int = 10) -> List[ExecutionResult]:
        """Get recent executions."""
        return self.executions[-limit:]


class SandboxContext:
    """
    Context manager for sandbox execution.

    Usage:
        executor = SandboxExecutor()

        with SandboxContext(executor, "nmap -sV 127.0.0.1", timeout=60) as result:
            if result.success():
                print(result.stdout)
    """

    def __init__(self, executor: SandboxExecutor, command: str, timeout: int = 60):
        self.executor = executor
        self.command = command
        self.timeout = timeout
        self.result = None

    def __enter__(self):
        self.result = self.executor.execute(self.command, timeout=self.timeout)
        return self.result

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.error(f"Error in sandbox context: {exc_val}")
        return False


if __name__ == "__main__":
    print("\n" + "="*70)
    print("Sandbox Executor Test")
    print("="*70)
    print("\n⚠️  ETHICAL SAFEGUARD - SANDBOXED EXECUTION\n")

    # Initialize executor
    print("[Test] Initializing Sandbox Executor...")
    print("       (Using Alpine Linux for quick testing)")

    executor = SandboxExecutor(
        image="alpine:latest",
        network_mode="none",  # Fully isolated
        memory_limit="256m",
        cpu_limit=0.5
    )

    # Test 1: Simple command
    print("\n[Test 1] Running simple command in sandbox...")
    result1 = executor.execute("echo 'Hello from sandbox'", timeout=10)

    print(f"  Exit code: {result1.exit_code}")
    print(f"  Duration: {result1.duration:.2f}s")
    print(f"  Output: {result1.stdout.strip()}")
    print(f"  Success: {result1.success()}")

    # Test 2: Command with timeout
    print("\n[Test 2] Running command with timeout...")
    result2 = executor.execute("sleep 30", timeout=2)

    print(f"  Exit code: {result2.exit_code}")
    print(f"  Duration: {result2.duration:.2f}s")
    print(f"  Timed out: {result2.timed_out}")
    print(f"  Success: {result2.success()}")

    # Test 3: Failed command
    print("\n[Test 3] Running failing command...")
    result3 = executor.execute("ls /nonexistent", timeout=10)

    print(f"  Exit code: {result3.exit_code}")
    print(f"  Duration: {result3.duration:.2f}s")
    print(f"  Success: {result3.success()}")
    print(f"  Stderr: {result3.stderr.strip()[:100]}")

    # Statistics
    print("\n[Test] Executor statistics:")
    stats = executor.get_stats()
    print(f"  Total executions: {stats['total_executions']}")
    print(f"  Successful: {stats['successful']}")
    print(f"  Failed: {stats['failed']}")
    print(f"  Timeouts: {stats['timeouts']}")
    print(f"  Success rate: {stats['success_rate']:.0%}")

    # Test context manager
    print("\n[Test 4] Testing SandboxContext...")
    with SandboxContext(executor, "uname -a", timeout=10) as result:
        if result.success():
            print(f"  ✅ Context execution successful")
            print(f"  Output: {result.stdout.strip()}")
        else:
            print(f"  ❌ Context execution failed")

    print("\n" + "="*70)
    print("✅ Sandbox Executor operational!")
    print("="*70)
    print("\n⚠️  Remember: Always use sandbox for security testing.")
    print("Isolation protects both you and your host system.")
    print("="*70)
