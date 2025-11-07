#!/usr/bin/env python3
"""
Configuration Manager for MindSync Oracle

Handles loading, validation, and access to configuration.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
import logging
from string import Template

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages MindSync Oracle configuration."""

    def __init__(self, config_path: str = "config.yaml"):
        """Load configuration from YAML file."""
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._validate_config()
        logger.info(f"Configuration loaded from {config_path}")

    def _load_config(self) -> Dict[str, Any]:
        """Load and parse YAML configuration."""
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}, using defaults")
            return self._default_config()

        try:
            with open(self.config_path) as f:
                config_text = f.read()

            # Substitute environment variables
            config_text = self._substitute_env_vars(config_text)

            config = yaml.safe_load(config_text)
            return config

        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self._default_config()

    def _substitute_env_vars(self, text: str) -> str:
        """Replace ${VAR} with environment variable values."""
        # Simple replacement for ${VAR} patterns
        import re

        def replace_var(match):
            var_name = match.group(1)
            return os.getenv(var_name, f"${{{var_name}}}")  # Keep placeholder if not found

        return re.sub(r'\$\{([^}]+)\}', replace_var, text)

    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            'api': {
                'anthropic_key': os.getenv('ANTHROPIC_API_KEY', ''),
                'openai_key': os.getenv('OPENAI_API_KEY', '')
            },
            'database': {
                'path': 'mindsync_memory.db',
                'backup_enabled': False
            },
            'agent': {
                'model': 'claude-sonnet-4-5-20250929',
                'max_tokens': 8000,
                'temperature': 0.7
            },
            'goals': {
                'check_interval_seconds': 60,
                'max_concurrent_goals': 3,
                'auto_decompose': True
            },
            'hexstrike': {
                'enabled': False,
                'server_url': 'http://localhost:8888'
            },
            'scheduler': {
                'enabled': False
            },
            'notifications': {
                'enabled': True,
                'methods': ['terminal']
            },
            'logging': {
                'level': 'INFO',
                'file': 'mindsync.log'
            }
        }

    def _validate_config(self):
        """Validate required configuration."""
        # Check for required API key
        if not self.get('api.anthropic_key') and not self.get('development.mock_api_calls'):
            logger.warning("ANTHROPIC_API_KEY not set - Claude features will be limited")

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Example: config.get('api.anthropic_key')
        """
        keys = key_path.split('.')
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any):
        """Set configuration value using dot notation."""
        keys = key_path.split('.')
        config = self.config

        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        config[keys[-1]] = value

    def save(self):
        """Save current configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            logger.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving config: {e}")

    @property
    def anthropic_key(self) -> Optional[str]:
        """Get Anthropic API key."""
        key = self.get('api.anthropic_key')
        return key if key and key != '${ANTHROPIC_API_KEY}' else None

    @property
    def openai_key(self) -> Optional[str]:
        """Get OpenAI API key."""
        key = self.get('api.openai_key')
        return key if key and key != '${OPENAI_API_KEY}' else None

    @property
    def hexstrike_enabled(self) -> bool:
        """Check if HexStrike integration is enabled."""
        return self.get('hexstrike.enabled', False)

    @property
    def scheduler_enabled(self) -> bool:
        """Check if background scheduler is enabled."""
        return self.get('scheduler.enabled', False)

    def __repr__(self) -> str:
        return f"ConfigManager(config_path='{self.config_path}')"


# Global config instance
_config: Optional[ConfigManager] = None


def get_config(config_path: str = "config.yaml") -> ConfigManager:
    """Get or create global config instance."""
    global _config
    if _config is None:
        _config = ConfigManager(config_path)
    return _config


if __name__ == "__main__":
    # Test config loading
    logging.basicConfig(level=logging.INFO)

    config = ConfigManager("config.yaml")

    print(f"Anthropic Key: {config.anthropic_key[:20] if config.anthropic_key else 'Not set'}...")
    print(f"Database Path: {config.get('database.path')}")
    print(f"HexStrike Enabled: {config.hexstrike_enabled}")
    print(f"Scheduler Enabled: {config.scheduler_enabled}")
    print(f"Model: {config.get('agent.model')}")
