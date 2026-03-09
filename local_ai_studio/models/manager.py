"""
Model management: discovery, download, loading, and lifecycle.

Supports GGUF models (via llama-cpp-python), Ollama integration,
and HuggingFace Hub downloads. Tracks available models and their metadata.
"""

import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Generator, Optional

from local_ai_studio.config import StudioConfig
from local_ai_studio.hardware import build_hardware_profile, detect_gpu

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ModelCard:
    """Metadata for a locally available model."""
    name: str
    path: str
    format: str = "gguf"            # gguf | safetensors | pytorch | ollama
    size_bytes: int = 0
    parameter_count: str = ""       # e.g. "7B", "13B"
    quantization: str = ""          # e.g. "Q4_K_M", "Q5_K_M"
    context_length: int = 0
    architecture: str = ""          # e.g. "llama", "mistral", "codellama"
    tags: list[str] = field(default_factory=list)
    source: str = ""                # HuggingFace repo, URL, or "ollama"
    sha256: str = ""
    added_timestamp: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LoadedModel:
    """Represents a currently loaded model in memory."""
    card: ModelCard
    backend: str = "llama_cpp"      # llama_cpp | ollama
    handle: Any = None              # The actual model object
    lora_adapters: list[str] = field(default_factory=list)
    gpu_layers: int = -1
    context_length: int = 8192


# ---------------------------------------------------------------------------
# Registry: keeps track of all available models on disk
# ---------------------------------------------------------------------------

class ModelRegistry:
    """Scans and maintains an index of locally available models."""

    def __init__(self, config: StudioConfig):
        self.config = config
        self.models_dir = Path(config.get("models_dir"))
        self._index_path = self.models_dir / "model_index.json"
        self._index: dict[str, ModelCard] = {}
        self._load_index()

    def scan(self) -> list[ModelCard]:
        """Scan models_dir for GGUF/safetensors files and update the index."""
        self.models_dir.mkdir(parents=True, exist_ok=True)

        found: dict[str, ModelCard] = {}
        for root, _dirs, files in os.walk(self.models_dir):
            for filename in files:
                if filename == "model_index.json":
                    continue
                ext = Path(filename).suffix.lower()
                if ext not in (".gguf", ".safetensors", ".bin", ".pt"):
                    continue
                full_path = os.path.join(root, filename)
                card = self._card_from_file(full_path)
                found[card.path] = card

        # Merge: keep existing metadata for known models, add new ones
        for path, card in found.items():
            if path in self._index:
                # Preserve user tags / metadata
                card.tags = self._index[path].tags
                card.metadata = self._index[path].metadata
                card.added_timestamp = self._index[path].added_timestamp
            else:
                card.added_timestamp = time.time()
            self._index[path] = card

        # Remove entries whose files no longer exist
        self._index = {p: c for p, c in self._index.items() if os.path.exists(p)}
        self._save_index()
        return list(self._index.values())

    def list_models(self) -> list[ModelCard]:
        """Return all indexed models."""
        return list(self._index.values())

    def get_model(self, name_or_path: str) -> Optional[ModelCard]:
        """Look up a model by name or path."""
        if name_or_path in self._index:
            return self._index[name_or_path]
        for card in self._index.values():
            if card.name == name_or_path:
                return card
        return None

    def add_model(self, card: ModelCard) -> None:
        """Manually register a model."""
        card.added_timestamp = card.added_timestamp or time.time()
        self._index[card.path] = card
        self._save_index()

    def remove_model(self, name_or_path: str, delete_file: bool = False) -> bool:
        """Remove a model from the index (optionally delete the file)."""
        card = self.get_model(name_or_path)
        if card is None:
            return False
        if delete_file and os.path.exists(card.path):
            os.remove(card.path)
        self._index.pop(card.path, None)
        self._save_index()
        return True

    def tag_model(self, name_or_path: str, tags: list[str]) -> bool:
        """Add tags to a model."""
        card = self.get_model(name_or_path)
        if card is None:
            return False
        card.tags = list(set(card.tags + tags))
        self._save_index()
        return True

    # -- internals -----------------------------------------------------------

    def _card_from_file(self, filepath: str) -> ModelCard:
        """Create a ModelCard by inspecting a model file."""
        p = Path(filepath)
        name = p.stem
        size_bytes = p.stat().st_size
        fmt = p.suffix.lstrip(".").lower()
        if fmt in ("bin", "pt"):
            fmt = "pytorch"

        quant = self._guess_quantization(name)
        params = self._guess_params(name)
        arch = self._guess_architecture(name)

        return ModelCard(
            name=name,
            path=filepath,
            format=fmt,
            size_bytes=size_bytes,
            parameter_count=params,
            quantization=quant,
            architecture=arch,
        )

    @staticmethod
    def _guess_quantization(name: str) -> str:
        patterns = [
            r"(Q[2-8]_K_[SML])",
            r"(Q[2-8]_[0-9])",
            r"(Q[2-8])",
            r"(F16|F32|FP16|FP32)",
            r"(GPTQ|AWQ|GGML)",
        ]
        upper = name.upper()
        for pat in patterns:
            m = re.search(pat, upper)
            if m:
                return m.group(1)
        return ""

    @staticmethod
    def _guess_params(name: str) -> str:
        m = re.search(r"(\d+)[Bb]", name)
        return f"{m.group(1)}B" if m else ""

    @staticmethod
    def _guess_architecture(name: str) -> str:
        lower = name.lower()
        known = [
            "llama", "mistral", "mixtral", "phi", "gemma", "qwen",
            "codellama", "deepseek", "starcoder", "yi", "falcon",
            "vicuna", "openchat", "solar", "orca", "neural", "command-r",
        ]
        for arch in known:
            if arch in lower:
                return arch
        return ""

    def _load_index(self) -> None:
        if self._index_path.exists():
            try:
                with open(self._index_path) as f:
                    raw = json.load(f)
                self._index = {k: ModelCard(**v) for k, v in raw.items()}
            except (json.JSONDecodeError, TypeError, OSError):
                self._index = {}

    def _save_index(self) -> None:
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        raw = {k: asdict(v) for k, v in self._index.items()}
        with open(self._index_path, "w") as f:
            json.dump(raw, f, indent=2)


# ---------------------------------------------------------------------------
# Downloader: pulls models from HuggingFace Hub
# ---------------------------------------------------------------------------

class ModelDownloader:
    """Download GGUF models from HuggingFace Hub."""

    @staticmethod
    def download_from_hf(
        repo_id: str,
        filename: str,
        dest_dir: str,
        token: Optional[str] = None,
        progress_callback=None,
    ) -> str:
        """Download a single file from a HuggingFace repo.

        Returns the local file path on success.
        """
        try:
            from huggingface_hub import hf_hub_download
            local_path = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                local_dir=dest_dir,
                token=token,
            )
            return local_path
        except ImportError:
            raise RuntimeError(
                "huggingface_hub is required for HF downloads. "
                "Install with: pip install huggingface-hub"
            )

    @staticmethod
    def search_hf_models(
        query: str,
        limit: int = 20,
        gguf_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Search HuggingFace Hub for models matching a query."""
        try:
            from huggingface_hub import HfApi
            api = HfApi()
            models = api.list_models(
                search=query,
                limit=limit,
                sort="downloads",
                direction=-1,
            )
            results = []
            for m in models:
                entry = {
                    "id": m.id,
                    "downloads": getattr(m, "downloads", 0),
                    "likes": getattr(m, "likes", 0),
                    "tags": getattr(m, "tags", []),
                }
                if gguf_only and "gguf" not in str(entry.get("tags", [])).lower():
                    # Also check the repo name itself
                    if "gguf" not in m.id.lower():
                        continue
                results.append(entry)
            return results
        except ImportError:
            raise RuntimeError(
                "huggingface_hub is required. Install with: pip install huggingface-hub"
            )

    @staticmethod
    def list_repo_files(repo_id: str, token: Optional[str] = None) -> list[str]:
        """List files in a HuggingFace repo (useful to pick a GGUF variant)."""
        try:
            from huggingface_hub import HfApi
            api = HfApi()
            files = api.list_repo_files(repo_id, token=token)
            return [f for f in files if f.endswith(".gguf")]
        except ImportError:
            raise RuntimeError(
                "huggingface_hub is required. Install with: pip install huggingface-hub"
            )


# ---------------------------------------------------------------------------
# Ollama integration
# ---------------------------------------------------------------------------

class OllamaManager:
    """Manage models through an Ollama installation (if available)."""

    @staticmethod
    def is_available() -> bool:
        return shutil.which("ollama") is not None

    @staticmethod
    def list_models() -> list[dict[str, str]]:
        if not OllamaManager.is_available():
            return []
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode != 0:
                return []
            lines = result.stdout.strip().split("\n")[1:]  # skip header
            models = []
            for line in lines:
                parts = line.split()
                if parts:
                    models.append({
                        "name": parts[0],
                        "size": parts[2] if len(parts) > 2 else "",
                        "modified": " ".join(parts[3:]) if len(parts) > 3 else "",
                    })
            return models
        except (subprocess.TimeoutExpired, OSError):
            return []

    @staticmethod
    def pull(model_name: str) -> bool:
        if not OllamaManager.is_available():
            return False
        try:
            result = subprocess.run(
                ["ollama", "pull", model_name],
                capture_output=True, text=True, timeout=600,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False

    @staticmethod
    def remove(model_name: str) -> bool:
        if not OllamaManager.is_available():
            return False
        try:
            result = subprocess.run(
                ["ollama", "rm", model_name],
                capture_output=True, text=True, timeout=30,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False


# ---------------------------------------------------------------------------
# Model loader: instantiates inference-ready model objects
# ---------------------------------------------------------------------------

class ModelLoader:
    """Load models into memory using the appropriate backend."""

    def __init__(self, config: StudioConfig):
        self.config = config
        self._current: Optional[LoadedModel] = None

    @property
    def current_model(self) -> Optional[LoadedModel]:
        return self._current

    def load_gguf(
        self,
        card: ModelCard,
        gpu_layers: int = -1,
        context_length: int = 8192,
        lora_path: Optional[str] = None,
    ) -> LoadedModel:
        """Load a GGUF model via llama-cpp-python."""
        try:
            from llama_cpp import Llama
        except ImportError:
            raise RuntimeError(
                "llama-cpp-python is required. Install with:\n"
                "  CMAKE_ARGS='-DGGML_CUDA=on' pip install llama-cpp-python\n"
                "Or for CPU only:\n"
                "  pip install llama-cpp-python"
            )

        # Unload previous model
        self.unload()

        hw = self.config.get("hardware", {})
        n_gpu_layers = gpu_layers if gpu_layers != -1 else hw.get("gpu_layers", -1)
        n_threads = hw.get("cpu_threads", 0) or None
        batch_size = hw.get("batch_size", 512)

        kwargs: dict[str, Any] = {
            "model_path": card.path,
            "n_ctx": context_length,
            "n_gpu_layers": n_gpu_layers,
            "n_batch": batch_size,
            "verbose": False,
        }
        if n_threads:
            kwargs["n_threads"] = n_threads
        if lora_path:
            kwargs["lora_path"] = lora_path

        llm = Llama(**kwargs)

        loaded = LoadedModel(
            card=card,
            backend="llama_cpp",
            handle=llm,
            gpu_layers=n_gpu_layers,
            context_length=context_length,
        )
        if lora_path:
            loaded.lora_adapters.append(lora_path)

        self._current = loaded

        # Update config active model
        self.config.set("active_model.path", card.path)
        self.config.set("active_model.name", card.name)
        self.config.set("active_model.format", card.format)

        return loaded

    def unload(self) -> None:
        """Release the current model from memory."""
        if self._current and self._current.handle:
            del self._current.handle
        self._current = None

    def generate(
        self,
        prompt: str,
        stream: bool = True,
        **kwargs,
    ) -> Generator[str, None, None] | str:
        """Generate text from the loaded model.

        If stream=True, yields token strings.
        If stream=False, returns the full response string.
        """
        if not self._current or not self._current.handle:
            raise RuntimeError("No model loaded")

        inference = self.config.get("inference", {})
        gen_kwargs: dict[str, Any] = {
            "max_tokens": kwargs.get("max_tokens", inference.get("max_tokens", 4096)),
            "temperature": kwargs.get("temperature", inference.get("temperature", 0.7)),
            "top_p": kwargs.get("top_p", inference.get("top_p", 0.9)),
            "top_k": kwargs.get("top_k", inference.get("top_k", 50)),
            "repeat_penalty": kwargs.get(
                "repetition_penalty", inference.get("repetition_penalty", 1.1)
            ),
            "stream": stream,
        }

        stop = kwargs.get("stop_sequences", inference.get("stop_sequences", []))
        if stop:
            gen_kwargs["stop"] = stop

        if self._current.backend == "llama_cpp":
            return self._generate_llama_cpp(prompt, gen_kwargs, stream)
        else:
            raise RuntimeError(f"Unsupported backend: {self._current.backend}")

    def _generate_llama_cpp(
        self, prompt: str, gen_kwargs: dict, stream: bool
    ) -> Generator[str, None, None] | str:
        llm = self._current.handle
        if stream:
            return self._stream_llama_cpp(llm, prompt, gen_kwargs)
        else:
            result = llm(prompt, **{k: v for k, v in gen_kwargs.items() if k != "stream"})
            return result["choices"][0]["text"]

    @staticmethod
    def _stream_llama_cpp(llm, prompt: str, gen_kwargs: dict) -> Generator[str, None, None]:
        gen_kwargs_no_stream = {k: v for k, v in gen_kwargs.items() if k != "stream"}
        for chunk in llm(prompt, stream=True, **gen_kwargs_no_stream):
            token = chunk["choices"][0]["text"]
            if token:
                yield token

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        stream: bool = True,
        **kwargs,
    ) -> Generator[str, None, None] | str:
        """OpenAI-compatible chat completion with the loaded model."""
        if not self._current or not self._current.handle:
            raise RuntimeError("No model loaded")

        inference = self.config.get("inference", {})
        gen_kwargs: dict[str, Any] = {
            "max_tokens": kwargs.get("max_tokens", inference.get("max_tokens", 4096)),
            "temperature": kwargs.get("temperature", inference.get("temperature", 0.7)),
            "top_p": kwargs.get("top_p", inference.get("top_p", 0.9)),
            "top_k": kwargs.get("top_k", inference.get("top_k", 50)),
            "repeat_penalty": kwargs.get(
                "repetition_penalty", inference.get("repetition_penalty", 1.1)
            ),
            "stream": stream,
        }

        if self._current.backend == "llama_cpp":
            llm = self._current.handle
            if stream:
                return self._stream_chat_llama_cpp(llm, messages, gen_kwargs)
            else:
                result = llm.create_chat_completion(
                    messages=messages,
                    **{k: v for k, v in gen_kwargs.items() if k != "stream"},
                )
                return result["choices"][0]["message"]["content"]
        else:
            raise RuntimeError(f"Unsupported backend: {self._current.backend}")

    @staticmethod
    def _stream_chat_llama_cpp(
        llm, messages: list[dict[str, str]], gen_kwargs: dict
    ) -> Generator[str, None, None]:
        gen_kwargs_no_stream = {k: v for k, v in gen_kwargs.items() if k != "stream"}
        for chunk in llm.create_chat_completion(
            messages=messages, stream=True, **gen_kwargs_no_stream
        ):
            delta = chunk["choices"][0].get("delta", {})
            content = delta.get("content", "")
            if content:
                yield content
