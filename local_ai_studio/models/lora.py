"""
LoRA / QLoRA adapter management.

Provides utilities to list, apply, and train LoRA adapters for
fine-tuning models on specialised tasks (code generation, creative writing, etc.).
"""

import json
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

from local_ai_studio.config import StudioConfig


@dataclass
class LoRAAdapter:
    """Metadata about a LoRA adapter."""
    name: str
    path: str
    base_model: str = ""          # name/arch the adapter was trained on
    rank: int = 16
    alpha: float = 32.0
    target_modules: list[str] = field(default_factory=lambda: ["q_proj", "v_proj"])
    description: str = ""
    tags: list[str] = field(default_factory=list)
    created_timestamp: float = 0.0
    training_config: dict[str, Any] = field(default_factory=dict)


class LoRAManager:
    """Manage LoRA adapters: index, apply, and prepare training configs."""

    def __init__(self, config: StudioConfig):
        self.config = config
        self.lora_dir = Path(config.get("lora_dir"))
        self._index_path = self.lora_dir / "lora_index.json"
        self._index: dict[str, LoRAAdapter] = {}
        self._load_index()

    def scan(self) -> list[LoRAAdapter]:
        """Scan the LoRA directory for adapter files."""
        self.lora_dir.mkdir(parents=True, exist_ok=True)
        found: dict[str, LoRAAdapter] = {}
        for item in self.lora_dir.iterdir():
            if item.is_dir():
                # Look for adapter_config.json (PEFT format)
                config_file = item / "adapter_config.json"
                if config_file.exists():
                    adapter = self._parse_peft_adapter(item)
                    found[str(item)] = adapter
            elif item.suffix in (".bin", ".gguf", ".safetensors"):
                # Standalone LoRA file
                adapter = LoRAAdapter(
                    name=item.stem,
                    path=str(item),
                    created_timestamp=item.stat().st_mtime,
                )
                found[str(item)] = adapter

        # Merge with existing index
        for path, adapter in found.items():
            if path in self._index:
                adapter.tags = self._index[path].tags
                adapter.description = self._index[path].description
            self._index[path] = adapter

        self._index = {p: a for p, a in self._index.items() if os.path.exists(p)}
        self._save_index()
        return list(self._index.values())

    def list_adapters(self) -> list[LoRAAdapter]:
        return list(self._index.values())

    def get_adapter(self, name_or_path: str) -> Optional[LoRAAdapter]:
        if name_or_path in self._index:
            return self._index[name_or_path]
        for adapter in self._index.values():
            if adapter.name == name_or_path:
                return adapter
        return None

    def add_adapter(self, adapter: LoRAAdapter) -> None:
        adapter.created_timestamp = adapter.created_timestamp or time.time()
        self._index[adapter.path] = adapter
        self._save_index()

    def remove_adapter(self, name_or_path: str) -> bool:
        adapter = self.get_adapter(name_or_path)
        if adapter is None:
            return False
        self._index.pop(adapter.path, None)
        self._save_index()
        return True

    def generate_training_config(
        self,
        base_model_path: str,
        adapter_name: str,
        task: str = "general",
        rank: int = 16,
        alpha: float = 32.0,
        epochs: int = 3,
        learning_rate: float = 2e-4,
        batch_size: int = 4,
        gradient_accumulation: int = 4,
        use_4bit: bool = True,
    ) -> dict[str, Any]:
        """Generate a training configuration dict for LoRA/QLoRA fine-tuning.

        This can be used with the transformers + peft libraries to train
        an adapter. The config dict can be saved and used as a script input.
        """
        target_modules = {
            "general": ["q_proj", "v_proj"],
            "code": ["q_proj", "k_proj", "v_proj", "o_proj"],
            "creative": ["q_proj", "v_proj", "gate_proj", "up_proj"],
        }.get(task, ["q_proj", "v_proj"])

        config = {
            "base_model": base_model_path,
            "adapter_name": adapter_name,
            "output_dir": str(self.lora_dir / adapter_name),
            "lora_config": {
                "r": rank,
                "lora_alpha": alpha,
                "target_modules": target_modules,
                "lora_dropout": 0.05,
                "bias": "none",
                "task_type": "CAUSAL_LM",
            },
            "training_args": {
                "num_train_epochs": epochs,
                "per_device_train_batch_size": batch_size,
                "gradient_accumulation_steps": gradient_accumulation,
                "learning_rate": learning_rate,
                "weight_decay": 0.01,
                "warmup_ratio": 0.03,
                "lr_scheduler_type": "cosine",
                "logging_steps": 10,
                "save_strategy": "epoch",
                "fp16": not use_4bit,
                "bf16": False,
                "gradient_checkpointing": True,
                "optim": "paged_adamw_8bit" if use_4bit else "adamw_torch",
            },
            "quantization": {
                "use_4bit": use_4bit,
                "bnb_4bit_compute_dtype": "float16",
                "bnb_4bit_quant_type": "nf4",
                "bnb_4bit_use_double_quant": True,
            } if use_4bit else None,
        }
        return config

    def save_training_config(self, config: dict[str, Any], path: Optional[str] = None) -> str:
        """Save a training config to JSON."""
        if path is None:
            name = config.get("adapter_name", "untitled")
            path = str(self.lora_dir / f"{name}_train_config.json")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(config, f, indent=2)
        return path

    # -- internals -----------------------------------------------------------

    def _parse_peft_adapter(self, adapter_dir: Path) -> LoRAAdapter:
        config_file = adapter_dir / "adapter_config.json"
        try:
            with open(config_file) as f:
                cfg = json.load(f)
        except (json.JSONDecodeError, OSError):
            cfg = {}
        return LoRAAdapter(
            name=adapter_dir.name,
            path=str(adapter_dir),
            rank=cfg.get("r", 16),
            alpha=cfg.get("lora_alpha", 32.0),
            target_modules=cfg.get("target_modules", ["q_proj", "v_proj"]),
            base_model=cfg.get("base_model_name_or_path", ""),
            created_timestamp=adapter_dir.stat().st_mtime,
            training_config=cfg,
        )

    def _load_index(self) -> None:
        if self._index_path.exists():
            try:
                with open(self._index_path) as f:
                    raw = json.load(f)
                self._index = {k: LoRAAdapter(**v) for k, v in raw.items()}
            except (json.JSONDecodeError, TypeError, OSError):
                self._index = {}

    def _save_index(self) -> None:
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        raw = {k: asdict(v) for k, v in self._index.items()}
        with open(self._index_path, "w") as f:
            json.dump(raw, f, indent=2)
