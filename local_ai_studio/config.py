"""
Configuration management for Local AI Studio.

Handles loading, saving, and validating all system configuration including
model settings, inference parameters, tool permissions, and GUI preferences.
All configuration is persisted as JSON for portability.
"""

import json
import os
import copy
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Default directory layout
# ---------------------------------------------------------------------------
DEFAULT_DATA_DIR = Path.home() / ".local_ai_studio"
DEFAULT_MODELS_DIR = DEFAULT_DATA_DIR / "models"
DEFAULT_CONVERSATIONS_DIR = DEFAULT_DATA_DIR / "conversations"
DEFAULT_LORA_DIR = DEFAULT_DATA_DIR / "lora_adapters"
DEFAULT_PROFILES_DIR = DEFAULT_DATA_DIR / "profiles"
DEFAULT_SANDBOX_DIR = DEFAULT_DATA_DIR / "sandbox"
DEFAULT_LOGS_DIR = DEFAULT_DATA_DIR / "logs"

# ---------------------------------------------------------------------------
# Inference presets keyed by use-case
# ---------------------------------------------------------------------------
INFERENCE_PRESETS: dict[str, dict[str, Any]] = {
    "code": {
        "temperature": 0.15,
        "top_p": 0.9,
        "top_k": 40,
        "repetition_penalty": 1.05,
        "max_tokens": 4096,
        "description": "Low temperature for deterministic code generation",
    },
    "research": {
        "temperature": 0.4,
        "top_p": 0.92,
        "top_k": 50,
        "repetition_penalty": 1.1,
        "max_tokens": 4096,
        "description": "Balanced settings for analytical research tasks",
    },
    "creative": {
        "temperature": 0.9,
        "top_p": 0.95,
        "top_k": 80,
        "repetition_penalty": 1.15,
        "max_tokens": 4096,
        "description": "Higher temperature for creative and narrative writing",
    },
    "roleplay": {
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 100,
        "repetition_penalty": 1.18,
        "max_tokens": 4096,
        "description": "High creativity with repetition control for roleplay",
    },
    "balanced": {
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 50,
        "repetition_penalty": 1.1,
        "max_tokens": 4096,
        "description": "General-purpose balanced settings",
    },
}

# ---------------------------------------------------------------------------
# System prompt templates
# ---------------------------------------------------------------------------
SYSTEM_PROMPT_TEMPLATES: dict[str, str] = {
    "code_assistant": (
        "You are an expert software engineer. Provide clear, correct, and "
        "well-structured code. Explain your reasoning when asked. Follow best "
        "practices and prioritize readability and maintainability."
    ),
    "research_analyst": (
        "You are a research analyst. Provide thorough, evidence-based answers. "
        "Cite sources when possible. Structure responses with clear headings "
        "and bullet points. Acknowledge uncertainty where appropriate."
    ),
    "creative_writer": (
        "You are a creative writing assistant. Craft vivid, engaging prose "
        "with strong character development and compelling narratives. Adapt "
        "your style to match the requested genre and tone."
    ),
    "roleplay": (
        "You are a versatile roleplay partner. Stay in character, maintain "
        "narrative consistency, and respond creatively to scenario developments. "
        "Respect the established setting and character traits."
    ),
    "data_analyst": (
        "You are a data analyst. Provide precise, methodical analysis. "
        "Use structured outputs (tables, lists, JSON) when appropriate. "
        "Explain statistical concepts clearly and suggest visualizations."
    ),
    "general": (
        "You are a helpful, knowledgeable AI assistant. Provide accurate, "
        "concise responses tailored to the user's needs."
    ),
}

# ---------------------------------------------------------------------------
# Default full configuration
# ---------------------------------------------------------------------------
DEFAULT_CONFIG: dict[str, Any] = {
    "version": "1.0.0",
    # ---- Paths ----
    "data_dir": str(DEFAULT_DATA_DIR),
    "models_dir": str(DEFAULT_MODELS_DIR),
    "conversations_dir": str(DEFAULT_CONVERSATIONS_DIR),
    "lora_dir": str(DEFAULT_LORA_DIR),
    "profiles_dir": str(DEFAULT_PROFILES_DIR),
    "sandbox_dir": str(DEFAULT_SANDBOX_DIR),
    "logs_dir": str(DEFAULT_LOGS_DIR),
    # ---- Hardware ----
    "hardware": {
        "gpu_layers": -1,  # -1 = auto (offload as many layers as VRAM allows)
        "cpu_threads": 0,  # 0 = auto-detect
        "batch_size": 512,
        "use_mmap": True,
        "use_mlock": False,
        "gpu_memory_limit_mb": 0,  # 0 = no artificial cap
        "cpu_fallback": True,
    },
    # ---- Inference defaults ----
    "inference": {
        "preset": "balanced",
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 50,
        "repetition_penalty": 1.1,
        "max_tokens": 4096,
        "context_length": 8192,
        "stream": True,
        "stop_sequences": [],
    },
    # ---- Active model ----
    "active_model": {
        "path": "",
        "name": "",
        "format": "gguf",
        "lora_adapters": [],
    },
    # ---- System prompt ----
    "system_prompt": {
        "template": "general",
        "custom": "",
    },
    # ---- Tool permissions ----
    "tools": {
        "python_sandbox": {
            "enabled": True,
            "allowed_packages": [
                "numpy", "pandas", "matplotlib", "seaborn",
                "scikit-learn", "scipy", "requests", "json",
                "csv", "re", "math", "statistics", "collections",
                "itertools", "functools", "datetime", "pathlib",
            ],
            "max_execution_time": 30,
            "max_memory_mb": 512,
        },
        "filesystem": {
            "enabled": True,
            "allowed_roots": [str(DEFAULT_SANDBOX_DIR)],
            "allow_write": True,
            "allow_delete": False,
        },
        "web": {
            "enabled": True,
            "allow_urls": ["*"],
            "block_urls": [],
            "max_response_size_mb": 10,
            "timeout": 30,
        },
        "database": {
            "enabled": True,
            "allowed_types": ["sqlite"],
            "max_rows": 10000,
        },
        "git": {
            "enabled": True,
            "allowed_operations": [
                "status", "log", "diff", "add", "commit",
                "branch", "checkout", "pull", "push", "stash",
            ],
        },
        "shell": {
            "enabled": False,
            "allowed_commands": [],
            "blocked_commands": [
                "rm -rf /", "mkfs", "dd", ":(){ :|:& };:",
                "shutdown", "reboot", "halt", "poweroff",
            ],
        },
    },
    # ---- MCP server ----
    "mcp": {
        "enabled": True,
        "host": "127.0.0.1",
        "port": 8765,
        "max_concurrent": 4,
    },
    # ---- GUI ----
    "gui": {
        "host": "127.0.0.1",
        "port": 7860,
        "theme": "dark",
        "share": False,
    },
    # ---- Logging ----
    "logging": {
        "level": "INFO",
        "log_tool_calls": True,
        "log_file": str(DEFAULT_LOGS_DIR / "studio.log"),
    },
}


class StudioConfig:
    """Manages studio configuration with load/save/merge semantics."""

    def __init__(self, config_path: Optional[str] = None):
        self._path = Path(config_path) if config_path else DEFAULT_DATA_DIR / "config.json"
        self._data: dict[str, Any] = copy.deepcopy(DEFAULT_CONFIG)
        self._ensure_dirs()
        if self._path.exists():
            self.load()

    # -- public API ----------------------------------------------------------

    def get(self, dotted_key: str, default: Any = None) -> Any:
        """Retrieve a value using dot-notation, e.g. 'inference.temperature'."""
        keys = dotted_key.split(".")
        node: Any = self._data
        for k in keys:
            if isinstance(node, dict) and k in node:
                node = node[k]
            else:
                return default
        return node

    def set(self, dotted_key: str, value: Any) -> None:
        """Set a value using dot-notation and persist."""
        keys = dotted_key.split(".")
        node = self._data
        for k in keys[:-1]:
            if k not in node or not isinstance(node[k], dict):
                node[k] = {}
            node = node[k]
        node[keys[-1]] = value
        self.save()

    def load(self) -> None:
        """Load config from disk, merging with defaults for any missing keys."""
        try:
            with open(self._path, "r") as f:
                loaded = json.load(f)
            self._data = self._deep_merge(copy.deepcopy(DEFAULT_CONFIG), loaded)
        except (json.JSONDecodeError, OSError):
            self._data = copy.deepcopy(DEFAULT_CONFIG)

    def save(self) -> None:
        """Persist current configuration to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(self._data, f, indent=2, default=str)

    def export_profile(self, name: str) -> Path:
        """Export current config as a named profile."""
        profiles_dir = Path(self._data["profiles_dir"])
        profiles_dir.mkdir(parents=True, exist_ok=True)
        profile_path = profiles_dir / f"{name}.json"
        with open(profile_path, "w") as f:
            json.dump(self._data, f, indent=2, default=str)
        return profile_path

    def import_profile(self, path: str) -> None:
        """Import a profile from a JSON file."""
        with open(path, "r") as f:
            loaded = json.load(f)
        self._data = self._deep_merge(copy.deepcopy(DEFAULT_CONFIG), loaded)
        self.save()

    def apply_preset(self, preset_name: str) -> bool:
        """Apply an inference preset by name. Returns True on success."""
        if preset_name not in INFERENCE_PRESETS:
            return False
        preset = INFERENCE_PRESETS[preset_name]
        for key in ("temperature", "top_p", "top_k", "repetition_penalty", "max_tokens"):
            if key in preset:
                self._data["inference"][key] = preset[key]
        self._data["inference"]["preset"] = preset_name
        self.save()
        return True

    def get_system_prompt(self) -> str:
        """Return the effective system prompt (custom overrides template)."""
        custom = self._data["system_prompt"].get("custom", "")
        if custom:
            return custom
        template = self._data["system_prompt"].get("template", "general")
        return SYSTEM_PROMPT_TEMPLATES.get(template, SYSTEM_PROMPT_TEMPLATES["general"])

    @property
    def data(self) -> dict[str, Any]:
        return self._data

    # -- internal helpers ----------------------------------------------------

    def _ensure_dirs(self) -> None:
        """Create all required directories."""
        for key in (
            "data_dir", "models_dir", "conversations_dir",
            "lora_dir", "profiles_dir", "sandbox_dir", "logs_dir",
        ):
            Path(self._data[key]).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """Recursively merge *override* into *base*."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                base[key] = StudioConfig._deep_merge(base[key], value)
            else:
                base[key] = value
        return base
