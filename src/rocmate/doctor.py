"""System diagnostic checks."""

from __future__ import annotations

import os
import shutil
import subprocess

try:
    import grp

    _HAS_GRP = True
except ImportError:
    _HAS_GRP = False
from dataclasses import dataclass, field
from enum import Enum

from rich.console import Console

from rocmate import gpu as gpu_module


class Status(str, Enum):
    OK = "ok"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class CheckResult:
    name: str
    status: Status
    message: str
    fix: str | None = None


@dataclass
class DiagnosticReport:
    gpu_info: list[gpu_module.GpuInfo] = field(default_factory=list)
    rocm_version: str | None = None
    checks: list[CheckResult] = field(default_factory=list)

    def has_blocking_issues(self) -> bool:
        return any(c.status == Status.FAIL for c in self.checks)


def _check_groups(username: str | None = None) -> list[CheckResult]:
    """Verify the user is in 'render' and 'video' groups (Linux only)."""
    if not _HAS_GRP:
        return []
    if username is None:
        username = os.environ.get("USER", "")
    if not username:
        return []
    try:
        user_groups = {g.gr_name for g in grp.getgrall() if username in g.gr_mem}
    except OSError:
        return []
    results: list[CheckResult] = []
    for required in ("render", "video"):
        if required in user_groups:
            results.append(
                CheckResult(
                    name=f"group:{required}",
                    status=Status.OK,
                    message=f"User in '{required}' group",
                )
            )
        else:
            results.append(
                CheckResult(
                    name=f"group:{required}",
                    status=Status.FAIL,
                    message=f"User not in '{required}' group",
                    fix=f"sudo usermod -aG {required} $USER && newgrp {required}",
                )
            )
    return results


def _check_env_vars(gpu_info: list[gpu_module.GpuInfo]) -> list[CheckResult]:
    """Check for recommended ENV vars based on GPU."""
    results: list[CheckResult] = []
    if not gpu_info:
        return results
    # Only suggest HSA_OVERRIDE for known-tricky chips
    tricky_chips = {"gfx1034", "gfx1031", "gfx1032"}
    has_tricky = any(g.gfx_version in tricky_chips for g in gpu_info)
    if has_tricky and "HSA_OVERRIDE_GFX_VERSION" not in os.environ:
        results.append(
            CheckResult(
                name="env:HSA_OVERRIDE_GFX_VERSION",
                status=Status.WARN,
                message="HSA_OVERRIDE_GFX_VERSION not set",
                fix="export HSA_OVERRIDE_GFX_VERSION=10.3.0",
            )
        )
    return results


def _run_check(cmd: list[str]) -> str | None:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
        return proc.stdout if proc.returncode == 0 else None
    except (subprocess.TimeoutExpired, OSError):
        return None


def _check_docker() -> list[CheckResult]:
    if not shutil.which("docker"):
        return [
            CheckResult(
                name="docker",
                status=Status.WARN,
                message="docker not installed — GPU passthrough not verifiable",
            )
        ]
    output = _run_check(
        [
            "docker",
            "run",
            "--rm",
            "--device=/dev/kfd",
            "--device=/dev/dri",
            "alpine",
            "ls",
            "/dev/kfd",
        ]
    )
    if output is not None:
        return [CheckResult("docker:gpu", Status.OK, "Docker GPU passthrough accessible")]
    return [
        CheckResult(
            name="docker:gpu",
            status=Status.WARN,
            message="Docker installed but GPU passthrough not verified",
            fix="Ensure /dev/kfd and /dev/dri are passed to containers and user is in 'docker' group",  # noqa: E501
        )
    ]


def _check_vulkan() -> list[CheckResult]:
    if not shutil.which("vulkaninfo"):
        return [
            CheckResult(
                name="vulkan",
                status=Status.WARN,
                message="vulkaninfo not installed — Vulkan support not verifiable",
            )
        ]
    output = _run_check(["vulkaninfo", "--summary"])
    if output and "AMD" in output:
        return [CheckResult("vulkan", Status.OK, "Vulkan: AMD device found")]
    return [
        CheckResult(
            name="vulkan",
            status=Status.WARN,
            message="Vulkan installed but no AMD device found in vulkaninfo output",
            fix="Install AMD Vulkan driver: sudo apt install mesa-vulkan-drivers",
        )
    ]


def run() -> DiagnosticReport:
    """Run all checks and return a diagnostic report."""
    report = DiagnosticReport()
    report.gpu_info = gpu_module.detect_amd_gpus()
    report.rocm_version = gpu_module.get_rocm_version()

    if not report.gpu_info:
        report.checks.append(
            CheckResult(
                name="gpu",
                status=Status.FAIL,
                message="No AMD GPU detected (rocminfo missing or no devices)",
                fix="Install ROCm: https://rocm.docs.amd.com/projects/install-on-linux/",
            )
        )
    else:
        for g in report.gpu_info:
            report.checks.append(
                CheckResult(
                    name="gpu",
                    status=Status.OK,
                    message=f"Detected: {g.name} ({g.gfx_version})",
                )
            )

    if report.rocm_version is None:
        report.checks.append(
            CheckResult(
                name="rocm",
                status=Status.FAIL,
                message="ROCm not installed or not on PATH",
                fix="Install ROCm: https://rocm.docs.amd.com/projects/install-on-linux/",
            )
        )
    else:
        report.checks.append(
            CheckResult(
                name="rocm",
                status=Status.OK,
                message=f"ROCm {report.rocm_version} installed",
            )
        )

    report.checks.extend(_check_groups())
    report.checks.extend(_check_env_vars(report.gpu_info))
    report.checks.extend(_check_docker())
    report.checks.extend(_check_vulkan())
    return report


_ICONS = {
    Status.OK: "[green]✓[/green]",
    Status.WARN: "[yellow]⚠[/yellow]",
    Status.FAIL: "[red]✗[/red]",
}


def render(report: DiagnosticReport, console: Console) -> None:
    """Pretty-print the report."""
    console.print("[bold]rocmate doctor[/bold]\n")
    for check in report.checks:
        icon = _ICONS[check.status]
        console.print(f"{icon} {check.message}")
        if check.fix:
            console.print(f"   [dim]→ {check.fix}[/dim]")
    console.print()
    fails = sum(1 for c in report.checks if c.status == Status.FAIL)
    warns = sum(1 for c in report.checks if c.status == Status.WARN)
    if fails:
        console.print(f"[red]{fails} blocking issue(s).[/red] Fix these to run AI workloads.")
    elif warns:
        console.print(
            f"[yellow]{warns} warning(s).[/yellow] System should work but optimisations recommended."  # noqa: E501
        )
    else:
        console.print("[green]All checks passed.[/green] Your system is ready.")
