"""
Python Environment Manager
Manage Python virtual environments and dependencies
"""

import logging
import subprocess
import venv
from pathlib import Path

logger = logging.getLogger(__name__)


class PythonEnvironmentManager:
    """Manage Python virtual environments and dependencies"""

    def __init__(self, base_dir: str = "/tmp/hexstrike_envs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

    def create_venv(self, env_name: str) -> Path:
        """Create a new virtual environment"""
        env_path = self.base_dir / env_name
        if not env_path.exists():
            logger.info(f"Creating virtual environment: {env_name}")
            venv.create(env_path, with_pip=True)
        return env_path

    def install_package(self, env_name: str, package: str) -> bool:
        """Install a package in the specified environment"""
        env_path = self.create_venv(env_name)
        pip_path = env_path / "bin" / "pip"

        try:
            result = subprocess.run([str(pip_path), "install", package],
                                  capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                logger.info(f"Installed package {package} in {env_name}")
                return True
            else:
                logger.error(f"Failed to install {package}: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error installing package {package}: {e}")
            return False

    def get_python_path(self, env_name: str) -> str:
        """Get Python executable path for environment"""
        env_path = self.create_venv(env_name)
        return str(env_path / "bin" / "python")
