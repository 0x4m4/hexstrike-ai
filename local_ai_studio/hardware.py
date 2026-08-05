"""
Hardware detection and monitoring for Local AI Studio.

Detects GPU (NVIDIA CUDA) and CPU capabilities, monitors VRAM/RAM usage,
and provides recommendations for model sizes and layer offloading.
"""

import os
import platform
import subprocess
import shutil
from dataclasses import dataclass, field
from typing import Optional

import psutil


@dataclass
class GPUInfo:
    """Information about a detected GPU."""
    name: str = "Unknown"
    vram_total_mb: int = 0
    vram_used_mb: int = 0
    vram_free_mb: int = 0
    cuda_available: bool = False
    cuda_version: str = ""
    driver_version: str = ""
    temperature_c: Optional[int] = None
    utilization_pct: Optional[int] = None
    power_draw_w: Optional[float] = None


@dataclass
class CPUInfo:
    """Information about the CPU."""
    name: str = "Unknown"
    cores_physical: int = 0
    cores_logical: int = 0
    architecture: str = ""
    ram_total_mb: int = 0
    ram_available_mb: int = 0
    is_arm: bool = False


@dataclass
class HardwareProfile:
    """Complete hardware profile for the system."""
    gpu: GPUInfo = field(default_factory=GPUInfo)
    cpu: CPUInfo = field(default_factory=CPUInfo)
    recommended_gpu_layers: int = 0
    recommended_threads: int = 4
    recommended_batch_size: int = 512
    recommended_context_length: int = 8192
    recommended_quant: str = "Q4_K_M"


def _run_nvidia_smi(query: str) -> Optional[str]:
    """Run nvidia-smi with a query and return stdout, or None on failure."""
    smi = shutil.which("nvidia-smi")
    if smi is None:
        return None
    try:
        result = subprocess.run(
            [smi, f"--query-gpu={query}", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None


def detect_gpu() -> GPUInfo:
    """Detect NVIDIA GPU information via nvidia-smi."""
    info = GPUInfo()

    # Name and VRAM
    raw = _run_nvidia_smi("name,memory.total,memory.used,memory.free")
    if raw:
        parts = [p.strip() for p in raw.split(",")]
        if len(parts) >= 4:
            info.name = parts[0]
            info.vram_total_mb = int(float(parts[1]))
            info.vram_used_mb = int(float(parts[2]))
            info.vram_free_mb = int(float(parts[3]))
            info.cuda_available = True

    # Driver and CUDA version
    raw = _run_nvidia_smi("driver_version,cuda_version")
    if raw:
        parts = [p.strip() for p in raw.split(",")]
        if len(parts) >= 2:
            info.driver_version = parts[0]
            info.cuda_version = parts[1]

    # Temp / utilisation / power
    raw = _run_nvidia_smi("temperature.gpu,utilization.gpu,power.draw")
    if raw:
        parts = [p.strip() for p in raw.split(",")]
        try:
            if len(parts) >= 1 and parts[0]:
                info.temperature_c = int(float(parts[0]))
            if len(parts) >= 2 and parts[1]:
                info.utilization_pct = int(float(parts[1]))
            if len(parts) >= 3 and parts[2]:
                info.power_draw_w = float(parts[2])
        except ValueError:
            pass

    return info


def detect_cpu() -> CPUInfo:
    """Detect CPU and RAM information."""
    info = CPUInfo()
    info.cores_physical = psutil.cpu_count(logical=False) or 1
    info.cores_logical = psutil.cpu_count(logical=True) or 1
    info.architecture = platform.machine()
    info.is_arm = info.architecture.lower() in ("aarch64", "arm64", "armv8l")

    mem = psutil.virtual_memory()
    info.ram_total_mb = int(mem.total / (1024 * 1024))
    info.ram_available_mb = int(mem.available / (1024 * 1024))

    # Try to get a friendly CPU name
    try:
        if os.path.exists("/proc/cpuinfo"):
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name"):
                        info.name = line.split(":", 1)[1].strip()
                        break
        if info.name == "Unknown":
            info.name = platform.processor() or "Unknown"
    except OSError:
        info.name = platform.processor() or "Unknown"

    return info


def _estimate_gguf_layer_vram_mb(param_billions: float, quant_bits: float) -> float:
    """Rough estimate of VRAM per transformer layer for a GGUF model."""
    # Very approximate: each layer ~ (params_per_layer * bits) / 8 / 1e6 MB
    # A 7B model has ~32 layers, so ~220M params/layer
    params_per_layer = (param_billions * 1e9) / 32
    return (params_per_layer * quant_bits) / 8 / (1024 * 1024)


def build_hardware_profile() -> HardwareProfile:
    """Build a complete hardware profile with recommendations."""
    gpu = detect_gpu()
    cpu = detect_cpu()
    profile = HardwareProfile(gpu=gpu, cpu=cpu)

    # Recommend thread count (leave 2 cores free for system / GUI)
    profile.recommended_threads = max(1, cpu.cores_physical - 2)

    if gpu.cuda_available and gpu.vram_total_mb > 0:
        vram = gpu.vram_total_mb

        # Quantization recommendation based on VRAM
        if vram >= 12000:
            profile.recommended_quant = "Q5_K_M"
            profile.recommended_context_length = 16384
            profile.recommended_batch_size = 1024
        elif vram >= 8000:
            profile.recommended_quant = "Q4_K_M"
            profile.recommended_context_length = 8192
            profile.recommended_batch_size = 512
        elif vram >= 6000:
            profile.recommended_quant = "Q4_K_S"
            profile.recommended_context_length = 4096
            profile.recommended_batch_size = 256
        else:
            profile.recommended_quant = "Q3_K_M"
            profile.recommended_context_length = 2048
            profile.recommended_batch_size = 128

        # GPU layers: offload as many as possible
        # For an 8 GB card with a 7B Q4_K_M model (~4.5 GB), all 33 layers fit
        profile.recommended_gpu_layers = -1  # let llama.cpp figure it out
    else:
        # CPU-only fallback
        profile.recommended_quant = "Q4_K_M"
        profile.recommended_context_length = 4096
        profile.recommended_batch_size = 256
        profile.recommended_gpu_layers = 0

    return profile


def get_vram_usage() -> dict:
    """Return current VRAM usage snapshot (for live monitoring in the GUI)."""
    gpu = detect_gpu()
    return {
        "total_mb": gpu.vram_total_mb,
        "used_mb": gpu.vram_used_mb,
        "free_mb": gpu.vram_free_mb,
        "utilization_pct": gpu.utilization_pct,
        "temperature_c": gpu.temperature_c,
        "power_draw_w": gpu.power_draw_w,
    }


def get_ram_usage() -> dict:
    """Return current RAM usage snapshot."""
    mem = psutil.virtual_memory()
    return {
        "total_mb": int(mem.total / (1024 * 1024)),
        "used_mb": int(mem.used / (1024 * 1024)),
        "available_mb": int(mem.available / (1024 * 1024)),
        "percent": mem.percent,
    }
