"""Tests for doctor diagnostics."""
from __future__ import annotations

import io
import os
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from rocmate import doctor
from rocmate.doctor import CheckResult, DiagnosticReport, Status
from rocmate.gpu import GpuInfo


# --- DiagnosticReport.has_blocking_issues ---

def test_no_checks_not_blocking():
    assert not DiagnosticReport().has_blocking_issues()


def test_only_ok_not_blocking():
    report = DiagnosticReport(checks=[CheckResult("gpu", Status.OK, "found")])
    assert not report.has_blocking_issues()


def test_warn_not_blocking():
    report = DiagnosticReport(checks=[CheckResult("env", Status.WARN, "not set")])
    assert not report.has_blocking_issues()


def test_fail_is_blocking():
    report = DiagnosticReport(checks=[CheckResult("gpu", Status.FAIL, "missing")])
    assert report.has_blocking_issues()


def test_mixed_fail_and_ok_is_blocking():
    report = DiagnosticReport(checks=[
        CheckResult("gpu", Status.OK, "found"),
        CheckResult("rocm", Status.FAIL, "missing"),
    ])
    assert report.has_blocking_issues()


# --- _check_env_vars ---

def test_no_warning_for_mainstream_chip():
    gpus = [GpuInfo("RX 7900 XTX", "gfx1100", 24576)]
    assert doctor._check_env_vars(gpus) == []


def test_no_warning_for_gfx1030():
    gpus = [GpuInfo("RX 6900 XT", "gfx1030", 16384)]
    assert doctor._check_env_vars(gpus) == []


def test_warns_for_tricky_chip_without_override():
    gpus = [GpuInfo("RX 5500 XT", "gfx1034", 8192)]
    with patch.dict(os.environ, {}, clear=True):
        results = doctor._check_env_vars(gpus)
    assert len(results) == 1
    assert results[0].status == Status.WARN
    assert "HSA_OVERRIDE_GFX_VERSION" in results[0].name


def test_no_warning_when_override_already_set():
    gpus = [GpuInfo("RX 5500 XT", "gfx1034", 8192)]
    with patch.dict(os.environ, {"HSA_OVERRIDE_GFX_VERSION": "10.3.0"}):
        results = doctor._check_env_vars(gpus)
    assert results == []


def test_empty_gpu_list_returns_empty():
    assert doctor._check_env_vars([]) == []


# --- _check_groups ---

def _make_mock_grp(groups: dict[str, list[str]]) -> MagicMock:
    """Build a mock grp module with the given {group_name: [members]} mapping."""
    mock_grp = MagicMock()
    mock_entries = [
        MagicMock(gr_name=name, gr_mem=members)
        for name, members in groups.items()
    ]
    mock_grp.getgrall.return_value = mock_entries
    return mock_grp


def test_check_groups_skipped_on_non_linux():
    with patch("rocmate.doctor._HAS_GRP", False):
        assert doctor._check_groups("testuser") == []


def test_check_groups_ok_when_in_both():
    mock_grp = _make_mock_grp({"render": ["testuser"], "video": ["testuser"]})
    with patch("rocmate.doctor._HAS_GRP", True), \
         patch("rocmate.doctor.grp", mock_grp, create=True):
        results = doctor._check_groups("testuser")
    assert len(results) == 2
    assert all(r.status == Status.OK for r in results)


def test_check_groups_fail_when_missing_render():
    mock_grp = _make_mock_grp({"render": [], "video": ["testuser"]})
    with patch("rocmate.doctor._HAS_GRP", True), \
         patch("rocmate.doctor.grp", mock_grp, create=True):
        results = doctor._check_groups("testuser")
    by_name = {r.name: r for r in results}
    assert by_name["group:render"].status == Status.FAIL
    assert by_name["group:video"].status == Status.OK


def test_check_groups_fail_fix_contains_usermod():
    mock_grp = _make_mock_grp({"render": [], "video": []})
    with patch("rocmate.doctor._HAS_GRP", True), \
         patch("rocmate.doctor.grp", mock_grp, create=True):
        results = doctor._check_groups("testuser")
    for r in results:
        if r.status == Status.FAIL:
            assert r.fix is not None
            assert "usermod" in r.fix


def test_check_groups_returns_empty_without_username():
    with patch("rocmate.doctor._HAS_GRP", True), \
         patch.dict(os.environ, {}, clear=True):
        results = doctor._check_groups(username=None)
    assert results == []


# --- run ---

def test_run_fail_when_no_gpu():
    with patch("rocmate.gpu.detect_amd_gpus", return_value=[]), \
         patch("rocmate.gpu.get_rocm_version", return_value=None):
        report = doctor.run()
    gpu_check = next(c for c in report.checks if c.name == "gpu")
    assert gpu_check.status == Status.FAIL


def test_run_fail_when_no_rocm():
    gpu = GpuInfo("RX 7900 XTX", "gfx1100", 24576)
    with patch("rocmate.gpu.detect_amd_gpus", return_value=[gpu]), \
         patch("rocmate.gpu.get_rocm_version", return_value=None):
        report = doctor.run()
    rocm_check = next(c for c in report.checks if c.name == "rocm")
    assert rocm_check.status == Status.FAIL


def test_run_ok_when_gpu_and_rocm_present():
    gpu = GpuInfo("RX 7900 XTX", "gfx1100", 24576)
    with patch("rocmate.gpu.detect_amd_gpus", return_value=[gpu]), \
         patch("rocmate.gpu.get_rocm_version", return_value="6.3.1"):
        report = doctor.run()
    gpu_check = next(c for c in report.checks if c.name == "gpu")
    rocm_check = next(c for c in report.checks if c.name == "rocm")
    assert gpu_check.status == Status.OK
    assert rocm_check.status == Status.OK


def test_run_gpu_check_contains_gfx_version():
    gpu = GpuInfo("RX 7900 XTX", "gfx1100", 24576)
    with patch("rocmate.gpu.detect_amd_gpus", return_value=[gpu]), \
         patch("rocmate.gpu.get_rocm_version", return_value="6.3.1"):
        report = doctor.run()
    gpu_check = next(c for c in report.checks if c.name == "gpu")
    assert "gfx1100" in gpu_check.message


# --- _check_docker ---

def test_docker_ok_when_available():
    with patch("rocmate.doctor.shutil.which", return_value="/usr/bin/docker"), \
         patch("rocmate.doctor._run_check", return_value="amdgpu"):
        results = doctor._check_docker()
    assert any(r.status == Status.OK for r in results)


def test_docker_warn_when_not_installed():
    with patch("rocmate.doctor.shutil.which", return_value=None):
        results = doctor._check_docker()
    assert len(results) == 1
    assert results[0].status == Status.WARN


def test_docker_warn_when_gpu_not_accessible():
    with patch("rocmate.doctor.shutil.which", return_value="/usr/bin/docker"), \
         patch("rocmate.doctor._run_check", return_value=None):
        results = doctor._check_docker()
    assert any(r.status == Status.WARN for r in results)


# --- _check_vulkan ---

def test_vulkan_ok_when_amd_device_found():
    with patch("rocmate.doctor.shutil.which", return_value="/usr/bin/vulkaninfo"), \
         patch("rocmate.doctor._run_check", return_value="deviceName = AMD Radeon RX 7900 XTX"):
        results = doctor._check_vulkan()
    assert any(r.status == Status.OK for r in results)


def test_vulkan_warn_when_vulkaninfo_missing():
    with patch("rocmate.doctor.shutil.which", return_value=None):
        results = doctor._check_vulkan()
    assert len(results) == 1
    assert results[0].status == Status.WARN


def test_vulkan_warn_when_no_amd_in_output():
    with patch("rocmate.doctor.shutil.which", return_value="/usr/bin/vulkaninfo"), \
         patch("rocmate.doctor._run_check", return_value="deviceName = llvmpipe"):
        results = doctor._check_vulkan()
    assert any(r.status == Status.WARN for r in results)


# --- render ---

def _render_report(report: DiagnosticReport) -> str:
    buf = io.StringIO()
    console = Console(file=buf, highlight=False, no_color=True)
    doctor.render(report, console)
    return buf.getvalue()


def test_render_shows_check_messages():
    report = DiagnosticReport(checks=[
        CheckResult("gpu", Status.OK, "GPU found"),
        CheckResult("rocm", Status.FAIL, "ROCm missing", fix="install rocm"),
    ])
    output = _render_report(report)
    assert "GPU found" in output
    assert "ROCm missing" in output


def test_render_shows_fix_hint():
    report = DiagnosticReport(checks=[
        CheckResult("rocm", Status.FAIL, "ROCm missing", fix="install rocm"),
    ])
    assert "install rocm" in _render_report(report)


def test_render_shows_blocking_summary_on_fail():
    report = DiagnosticReport(checks=[CheckResult("gpu", Status.FAIL, "No GPU")])
    assert "blocking" in _render_report(report).lower()


def test_render_shows_all_clear_on_ok():
    report = DiagnosticReport(checks=[CheckResult("gpu", Status.OK, "GPU found")])
    assert "passed" in _render_report(report).lower()


def test_render_shows_warning_summary():
    report = DiagnosticReport(checks=[CheckResult("env", Status.WARN, "override missing")])
    output = _render_report(report)
    assert "warning" in output.lower()
