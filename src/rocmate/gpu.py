"""AMD GPU detection — Linux (rocminfo) and Windows (hipinfo / WMI)."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class GpuInfo:
    name: str
    gfx_version: str  # e.g. "gfx1100"
    vram_mb: Optional[int]


# Ordered most-specific first so "RX 7900 XTX" matches before a hypothetical
# shorter prefix would.
_NAME_TO_GFX: list[tuple[str, str]] = [
    ("RX 9070", "gfx1201"),
    ("RX 7900", "gfx1100"),
    ("RX 7800", "gfx1101"),
    ("RX 7700", "gfx1101"),
    ("RX 7600", "gfx1102"),
    ("RX 6900", "gfx1030"),
    ("RX 6800", "gfx1030"),
    ("RX 6700", "gfx1031"),
    ("RX 6600", "gfx1032"),
    ("RX 5500", "gfx1034"),
    ("RX 5400", "gfx1034"),
]


def _gfx_from_name(name: str) -> Optional[str]:
    for substring, gfx in _NAME_TO_GFX:
        if substring in name:
            return gfx
    return None


def _run(cmd: list[str]) -> Optional[str]:
    if not shutil.which(cmd[0]):
        return None
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
    except (subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


# ---------------------------------------------------------------------------
# Linux detection (rocminfo)
# ---------------------------------------------------------------------------

def _detect_amd_gpus_linux() -> list[GpuInfo]:
    output = _run(["rocminfo"])
    if output is None:
        return []
    gpus: list[GpuInfo] = []
    blocks = re.split(r"\*{4,}\s*Agent\s+\d+\s*\*{4,}", output)
    for block in blocks:
        if "Device Type" not in block or "GPU" not in block:
            continue
        name_match = re.search(r"Marketing Name:\s*(.+)", block)
        gfx_match = re.search(r"Name:\s*(gfx\d{3,4}[a-z]?)", block)
        vram_match = re.search(r"Size:\s*(\d+)\(.*?\)\s*KB", block)
        if not gfx_match:
            continue
        vram_mb = int(vram_match.group(1)) // 1024 if vram_match else None
        gpus.append(GpuInfo(
            name=name_match.group(1).strip() if name_match else "Unknown AMD GPU",
            gfx_version=gfx_match.group(1).strip(),
            vram_mb=vram_mb,
        ))
    return gpus


# ---------------------------------------------------------------------------
# Windows detection (hipinfo primary, wmic fallback)
# ---------------------------------------------------------------------------

def _parse_hipinfo(output: str) -> list[GpuInfo]:
    """Parse `hipinfo` stdout into GpuInfo objects."""
    gpus: list[GpuInfo] = []
    blocks = re.split(r"Device\s+#\d+", output)
    for block in blocks:
        gfx_match = re.search(r"gcnArchName:\s*(\S+)", block)
        if not gfx_match:
            continue
        name_match = re.search(r"Device name:\s*(.+)", block)
        mem_match = re.search(r"totalGlobalMem:\s*(\d+)", block)
        vram_mb = int(mem_match.group(1)) // 1024 // 1024 if mem_match else None
        gpus.append(GpuInfo(
            name=name_match.group(1).strip() if name_match else "Unknown AMD GPU",
            gfx_version=gfx_match.group(1).strip(),
            vram_mb=vram_mb,
        ))
    return gpus


def _detect_via_wmi() -> list[GpuInfo]:
    """Detect AMD GPUs via wmic when hipinfo is unavailable."""
    output = _run([
        "wmic", "path", "Win32_VideoController",
        "get", "Name,AdapterRAM", "/format:list",
    ])
    if not output:
        return []
    gpus: list[GpuInfo] = []
    for block in output.split("\n\n"):
        name_match = re.search(r"Name=(.+)", block)
        if not name_match:
            continue
        name = name_match.group(1).strip()
        gfx = _gfx_from_name(name)
        if gfx is None:
            continue
        ram_match = re.search(r"AdapterRAM=(\d+)", block)
        vram_mb = int(ram_match.group(1)) // 1024 // 1024 if ram_match else None
        gpus.append(GpuInfo(name=name, gfx_version=gfx, vram_mb=vram_mb))
    return gpus


def _detect_amd_gpus_windows() -> list[GpuInfo]:
    output = _run(["hipinfo"])
    if output:
        gpus = _parse_hipinfo(output)
        if gpus:
            return gpus
    return _detect_via_wmi()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_amd_gpus() -> list[GpuInfo]:
    """Return all AMD GPUs detected. Empty list on failure."""
    if sys.platform == "win32":
        return _detect_amd_gpus_windows()
    return _detect_amd_gpus_linux()


def get_rocm_version() -> Optional[str]:
    """Return ROCm / HIP version string, or None if not found."""
    if sys.platform == "win32":
        hip_path = os.environ.get("HIP_PATH")
        if hip_path:
            try:
                with open(Path(hip_path) / "version") as f:
                    return f.read().strip()
            except OSError:
                pass
    else:
        try:
            with open("/opt/rocm/.info/version") as f:
                return f.read().strip()
        except OSError:
            pass

    output = _run(["hipcc", "--version"])
    if output:
        m = re.search(r"HIP version:\s*(\S+)", output)
        if m:
            return m.group(1)
    return None
