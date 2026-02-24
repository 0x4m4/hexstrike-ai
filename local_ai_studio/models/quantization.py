"""
Quantization utilities for converting and optimizing models.

Wraps llama.cpp's quantize tool and provides helpers for choosing
the right quantization level given VRAM constraints.
"""

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Quantization format metadata
# ---------------------------------------------------------------------------

@dataclass
class QuantFormat:
    """Describes a GGUF quantization format."""
    name: str
    bits_per_weight: float
    description: str
    recommended_min_vram_mb: int  # for a 7B model
    quality_rating: int           # 1-10 subjective quality


QUANT_FORMATS: dict[str, QuantFormat] = {
    "Q2_K": QuantFormat("Q2_K", 2.6, "Smallest, lowest quality", 2000, 3),
    "Q3_K_S": QuantFormat("Q3_K_S", 3.0, "Very small, low quality", 2500, 4),
    "Q3_K_M": QuantFormat("Q3_K_M", 3.3, "Small, decent quality", 2700, 5),
    "Q3_K_L": QuantFormat("Q3_K_L", 3.6, "Small, better quality", 2900, 5),
    "Q4_K_S": QuantFormat("Q4_K_S", 4.0, "Medium, good quality", 3200, 6),
    "Q4_K_M": QuantFormat("Q4_K_M", 4.5, "Medium, recommended balance", 3800, 7),
    "Q5_K_S": QuantFormat("Q5_K_S", 5.0, "Larger, very good quality", 4500, 8),
    "Q5_K_M": QuantFormat("Q5_K_M", 5.5, "Larger, excellent quality", 5000, 8),
    "Q6_K": QuantFormat("Q6_K", 6.5, "Large, near-lossless", 6000, 9),
    "Q8_0": QuantFormat("Q8_0", 8.0, "Full 8-bit, best GGUF quality", 7500, 10),
    "F16": QuantFormat("F16", 16.0, "16-bit float, reference quality", 14000, 10),
}


def recommend_quantization(vram_mb: int, param_billions: float = 7.0) -> list[str]:
    """Recommend quantization formats that fit within available VRAM.

    Scales the 7B baseline estimates by the actual parameter count.
    """
    scale = param_billions / 7.0
    fits = []
    for name, qf in QUANT_FORMATS.items():
        if qf.recommended_min_vram_mb * scale <= vram_mb:
            fits.append(name)
    return fits


def estimate_model_size_mb(
    param_billions: float, quant_format: str
) -> Optional[float]:
    """Estimate the on-disk size of a quantized model in MB."""
    qf = QUANT_FORMATS.get(quant_format)
    if qf is None:
        return None
    total_params = param_billions * 1e9
    size_bytes = total_params * qf.bits_per_weight / 8
    return size_bytes / (1024 * 1024)


def estimate_vram_mb(
    param_billions: float,
    quant_format: str,
    context_length: int = 8192,
) -> Optional[float]:
    """Rough VRAM estimate: model weights + KV cache overhead."""
    model_mb = estimate_model_size_mb(param_billions, quant_format)
    if model_mb is None:
        return None
    # KV cache: ~2 bytes per token per layer per head_dim, rough heuristic
    n_layers = 32 * (param_billions / 7)
    kv_mb = (context_length * n_layers * 128 * 2 * 2) / (1024 * 1024)
    return model_mb + kv_mb


# ---------------------------------------------------------------------------
# Quantize a model using llama.cpp's quantize binary
# ---------------------------------------------------------------------------

def find_llama_quantize() -> Optional[str]:
    """Locate the llama-quantize (or quantize) binary."""
    for name in ("llama-quantize", "quantize"):
        path = shutil.which(name)
        if path:
            return path
    # Common build locations
    for candidate in (
        os.path.expanduser("~/llama.cpp/build/bin/llama-quantize"),
        os.path.expanduser("~/llama.cpp/quantize"),
        "/usr/local/bin/llama-quantize",
    ):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def quantize_model(
    input_path: str,
    output_path: str,
    quant_type: str = "Q4_K_M",
    quantize_binary: Optional[str] = None,
) -> str:
    """Quantize a GGUF/FP16 model to a target quantization format.

    Returns the output path on success.
    Raises RuntimeError on failure.
    """
    binary = quantize_binary or find_llama_quantize()
    if binary is None:
        raise RuntimeError(
            "Could not find llama-quantize binary. Build llama.cpp or "
            "set the path manually."
        )

    if quant_type not in QUANT_FORMATS and quant_type.upper() not in QUANT_FORMATS:
        raise ValueError(f"Unknown quantization type: {quant_type}")

    result = subprocess.run(
        [binary, input_path, output_path, quant_type],
        capture_output=True, text=True, timeout=3600,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Quantization failed (exit {result.returncode}):\n{result.stderr}"
        )
    return output_path
