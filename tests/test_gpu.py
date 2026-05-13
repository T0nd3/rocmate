"""Tests for AMD GPU detection."""
from __future__ import annotations

import os
from unittest.mock import mock_open, patch

from rocmate import gpu

# Minimal rocminfo outputs that match the parser's regex
_ROCMINFO_ONE_GPU = """\
ROCk module is loaded

**** Agent 1 ****
  Name:                    Fake CPU
  Device Type:             CPU

**** Agent 2 ****
  Name:                    gfx1100
  Marketing Name:          AMD Radeon RX 7900 XTX
  Device Type:             GPU
  Size:                    25165824(0x1800000) KB
"""

_ROCMINFO_TWO_GPUS = """\
ROCk module is loaded

**** Agent 1 ****
  Name:                    gfx1100
  Marketing Name:          AMD Radeon RX 7900 XTX
  Device Type:             GPU
  Size:                    25165824(0x1800000) KB

**** Agent 2 ****
  Name:                    gfx1030
  Marketing Name:          AMD Radeon RX 6900 XT
  Device Type:             GPU
  Size:                    16777216(0x1000000) KB
"""

_ROCMINFO_NO_GPU = """\
ROCk module is loaded

**** Agent 1 ****
  Name:                    Fake CPU
  Device Type:             CPU
"""

_ROCMINFO_MISSING_MARKETING_NAME = """\
**** Agent 1 ****
  Name:                    gfx1030
  Device Type:             GPU
  Size:                    8388608(0x800000) KB
"""


# --- _detect_amd_gpus_linux (rocminfo parser) ---
# Call the private function directly — these tests verify the parser, not routing.

def test_detects_single_gpu():
    with patch("rocmate.gpu._run", return_value=_ROCMINFO_ONE_GPU):
        gpus = gpu._detect_amd_gpus_linux()
    assert len(gpus) == 1


def test_gfx_version_parsed_correctly():
    with patch("rocmate.gpu._run", return_value=_ROCMINFO_ONE_GPU):
        gpus = gpu._detect_amd_gpus_linux()
    assert gpus[0].gfx_version == "gfx1100"


def test_marketing_name_parsed_correctly():
    with patch("rocmate.gpu._run", return_value=_ROCMINFO_ONE_GPU):
        gpus = gpu._detect_amd_gpus_linux()
    assert gpus[0].name == "AMD Radeon RX 7900 XTX"


def test_vram_parsed_correctly():
    with patch("rocmate.gpu._run", return_value=_ROCMINFO_ONE_GPU):
        gpus = gpu._detect_amd_gpus_linux()
    assert gpus[0].vram_mb == 24576  # 25165824 KB // 1024


def test_detects_two_gpus():
    with patch("rocmate.gpu._run", return_value=_ROCMINFO_TWO_GPUS):
        gpus = gpu._detect_amd_gpus_linux()
    assert len(gpus) == 2
    gfx_versions = {g.gfx_version for g in gpus}
    assert gfx_versions == {"gfx1100", "gfx1030"}


def test_cpu_only_returns_empty():
    with patch("rocmate.gpu._run", return_value=_ROCMINFO_NO_GPU):
        assert gpu._detect_amd_gpus_linux() == []


def test_rocminfo_missing_returns_empty():
    with patch("rocmate.gpu._run", return_value=None):
        assert gpu._detect_amd_gpus_linux() == []


def test_missing_marketing_name_falls_back_to_unknown():
    with patch("rocmate.gpu._run", return_value=_ROCMINFO_MISSING_MARKETING_NAME):
        gpus = gpu._detect_amd_gpus_linux()
    assert len(gpus) == 1
    assert gpus[0].name == "Unknown AMD GPU"


# --- get_rocm_version ---
# Platform is patched explicitly so tests are deterministic on any OS.

def test_reads_version_file():
    with patch("builtins.open", mock_open(read_data="6.3.1\n")), \
         patch("rocmate.gpu.sys.platform", "linux"):
        version = gpu.get_rocm_version()
    assert version == "6.3.1"


def test_strips_whitespace_from_version_file():
    with patch("builtins.open", mock_open(read_data="  6.2.0  \n")), \
         patch("rocmate.gpu.sys.platform", "linux"):
        version = gpu.get_rocm_version()
    assert version == "6.2.0"


def test_falls_back_to_hipcc_when_file_missing():
    with patch("builtins.open", side_effect=OSError), \
         patch("rocmate.gpu.sys.platform", "linux"), \
         patch("rocmate.gpu._run", return_value="HIP version: 6.2.0\n"):
        version = gpu.get_rocm_version()
    assert version == "6.2.0"


def test_returns_none_when_nothing_available():
    with patch("builtins.open", side_effect=OSError), \
         patch("rocmate.gpu.sys.platform", "linux"), \
         patch("rocmate.gpu._run", return_value=None):
        version = gpu.get_rocm_version()
    assert version is None


def test_returns_none_when_hipcc_output_unparseable():
    with patch("builtins.open", side_effect=OSError), \
         patch("rocmate.gpu.sys.platform", "linux"), \
         patch("rocmate.gpu._run", return_value="some unexpected output\n"):
        version = gpu.get_rocm_version()
    assert version is None


# --- _run helper ---

def test_run_returns_none_when_command_not_found():
    with patch("rocmate.gpu.shutil.which", return_value=None):
        result = gpu._run(["rocminfo"])
    assert result is None


# =============================================================================
# Windows detection (v0.2)
# =============================================================================

_HIPINFO_ONE_GPU = """\
--------------------------------------------------------------------------------
device#                           0
Name:                             AMD Radeon RX 7900 XTX
totalGlobalMem:                   23.98 GB
gcnArchName:                      gfx1100
"""

_HIPINFO_TWO_GPUS = """\
--------------------------------------------------------------------------------
device#                           0
Name:                             AMD Radeon RX 7900 XTX
totalGlobalMem:                   23.98 GB
gcnArchName:                      gfx1100
--------------------------------------------------------------------------------
device#                           1
Name:                             AMD Radeon RX 6900 XT
totalGlobalMem:                   15.98 GB
gcnArchName:                      gfx1030
"""

_HIPINFO_NO_DEVICE = "No devices found.\n"

# wmic /format:list output (one AMD + one non-AMD card)
_WMIC_ONE_AMD = "AdapterRAM=25769803776\nName=AMD Radeon RX 7900 XTX\n"
_WMIC_NON_AMD = "AdapterRAM=8589934592\nName=NVIDIA GeForce RTX 4090\n"
_WMIC_TWO_CARDS = (
    "AdapterRAM=25769803776\nName=AMD Radeon RX 7900 XTX\n\n"
    "AdapterRAM=8589934592\nName=Intel UHD Graphics 630\n"
)


# --- _parse_hipinfo ---

class TestParseHipinfo:
    def test_single_gpu_count(self):
        assert len(gpu._parse_hipinfo(_HIPINFO_ONE_GPU)) == 1

    def test_gfx_version(self):
        assert gpu._parse_hipinfo(_HIPINFO_ONE_GPU)[0].gfx_version == "gfx1100"

    def test_device_name(self):
        assert gpu._parse_hipinfo(_HIPINFO_ONE_GPU)[0].name == "AMD Radeon RX 7900 XTX"

    def test_vram_gb_converted_to_mb(self):
        # 23.98 GB → int(23.98 * 1024) = 24555 MB
        assert gpu._parse_hipinfo(_HIPINFO_ONE_GPU)[0].vram_mb == 24555

    def test_two_gpus(self):
        gpus = gpu._parse_hipinfo(_HIPINFO_TWO_GPUS)
        assert len(gpus) == 2
        assert {g.gfx_version for g in gpus} == {"gfx1100", "gfx1030"}

    def test_no_device_returns_empty(self):
        assert gpu._parse_hipinfo(_HIPINFO_NO_DEVICE) == []

    def test_empty_string_returns_empty(self):
        assert gpu._parse_hipinfo("") == []


# --- _detect_via_wmi ---

class TestDetectViaWmi:
    def test_known_amd_gpu_returned(self):
        with patch("rocmate.gpu._run", return_value=_WMIC_ONE_AMD):
            gpus = gpu._detect_via_wmi()
        assert len(gpus) == 1
        assert gpus[0].gfx_version == "gfx1100"

    def test_vram_parsed_from_wmic(self):
        with patch("rocmate.gpu._run", return_value=_WMIC_ONE_AMD):
            gpus = gpu._detect_via_wmi()
        assert gpus[0].vram_mb == 24576

    def test_non_amd_gpu_excluded(self):
        with patch("rocmate.gpu._run", return_value=_WMIC_NON_AMD):
            assert gpu._detect_via_wmi() == []

    def test_mixed_cards_only_amd_returned(self):
        with patch("rocmate.gpu._run", return_value=_WMIC_TWO_CARDS):
            gpus = gpu._detect_via_wmi()
        assert len(gpus) == 1
        assert gpus[0].gfx_version == "gfx1100"

    def test_wmic_unavailable_returns_empty(self):
        with patch("rocmate.gpu._run", return_value=None):
            assert gpu._detect_via_wmi() == []


# --- _detect_amd_gpus_windows ---

class TestDetectAmdGpusWindows:
    def test_uses_hipinfo_when_available(self):
        with patch("rocmate.gpu._run", return_value=_HIPINFO_ONE_GPU):
            gpus = gpu._detect_amd_gpus_windows()
        assert gpus[0].gfx_version == "gfx1100"

    def test_falls_back_to_wmi_when_hipinfo_absent(self):
        def _side_effect(cmd: list[str]) -> str | None:
            if cmd[0] == "hipinfo":
                return None
            return _WMIC_ONE_AMD

        with patch("rocmate.gpu._run", side_effect=_side_effect):
            gpus = gpu._detect_amd_gpus_windows()
        assert gpus[0].gfx_version == "gfx1100"

    def test_returns_empty_when_both_unavailable(self):
        with patch("rocmate.gpu._run", return_value=None):
            assert gpu._detect_amd_gpus_windows() == []


# --- detect_amd_gpus platform routing ---

class TestDetectAmdGpusPlatformRouting:
    def test_routes_to_windows_on_win32(self):
        with patch("rocmate.gpu.sys.platform", "win32"), \
             patch("rocmate.gpu._detect_amd_gpus_windows", return_value=[]) as mock_win:
            gpu.detect_amd_gpus()
        mock_win.assert_called_once()

    def test_routes_to_linux_on_linux(self):
        with patch("rocmate.gpu.sys.platform", "linux"), \
             patch("rocmate.gpu._run", return_value=None) as mock_run:
            gpu.detect_amd_gpus()
        mock_run.assert_called_once_with(["rocminfo"])


# --- get_rocm_version Windows path ---

class TestGetRocmVersionWindows:
    def test_reads_hip_path_version_file(self):
        with patch("builtins.open", mock_open(read_data="6.2.0\n")), \
             patch("rocmate.gpu.sys.platform", "win32"), \
             patch.dict(os.environ, {"HIP_PATH": r"C:\Program Files\AMD\ROCm\6.2"}):
            version = gpu.get_rocm_version()
        assert version == "6.2.0"

    def test_falls_back_to_hipconfig_on_windows(self):
        def _open_side_effect(*_a, **_kw):
            raise OSError

        with patch("builtins.open", side_effect=_open_side_effect), \
             patch("rocmate.gpu.sys.platform", "win32"), \
             patch.dict(os.environ, {"HIP_PATH": r"C:\Program Files\AMD\ROCm\6.2"}), \
             patch("rocmate.gpu._run", return_value="HIP version: 6.2.60559-2985b26\n"):
            version = gpu.get_rocm_version()
        assert version == "6.2.60559-2985b26"
