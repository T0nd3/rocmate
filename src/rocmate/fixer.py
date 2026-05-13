"""Automated fix application for doctor check results."""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from rocmate.doctor import CheckResult


class FixKind(Enum):
    ENV_PROFILE = "env_profile"
    SUDO_COMMAND = "sudo_command"
    MANUAL = "manual"


@dataclass
class FixResult:
    check_name: str
    applied: bool
    message: str


def classify_fix(fix: str) -> FixKind:
    stripped = fix.strip()
    if stripped.startswith("export "):
        return FixKind.ENV_PROFILE
    if stripped.startswith("sudo "):
        return FixKind.SUDO_COMMAND
    return FixKind.MANUAL


def _detect_shell_profile() -> Path:
    shell = os.environ.get("SHELL", "")
    home = Path.home()
    if "zsh" in shell:
        return home / ".zshrc"
    if "fish" in shell:
        return home / ".config/fish/config.fish"
    return home / ".bashrc"


def fix_env_in_profile(name: str, value: str) -> FixResult:
    profile = _detect_shell_profile()
    export_line = f"export {name}={value}"
    try:
        content = profile.read_text() if profile.exists() else ""
        if export_line in content:
            return FixResult(name, False, f"Already set in {profile}")
        with open(profile, "a") as f:
            f.write(f"\n# Added by rocmate\n{export_line}\n")
        return FixResult(name, True, f"Added to {profile} — restart shell or run: source {profile}")
    except OSError as e:
        return FixResult(name, False, f"Failed to write {profile}: {e}")


def fix_sudo_command(check_name: str, cmd: str) -> FixResult:
    # Strip compound commands (&&) — e.g. `newgrp` requires a new shell session
    first_cmd = cmd.split("&&")[0].strip()
    result = subprocess.run(first_cmd, shell=True, check=False)
    if result.returncode == 0:
        return FixResult(check_name, True, f"Command succeeded — you may need to log out and back in")
    return FixResult(check_name, False, f"Command failed (exit {result.returncode}): {first_cmd}")


def apply_fix(check: CheckResult) -> Optional[FixResult]:
    if not check.fix:
        return None

    kind = classify_fix(check.fix)

    if kind == FixKind.ENV_PROFILE:
        # Parse "export KEY=VALUE"
        rest = check.fix[len("export "):].strip()
        if "=" in rest:
            name, _, value = rest.partition("=")
            return fix_env_in_profile(name.strip(), value.strip())

    if kind == FixKind.SUDO_COMMAND:
        return fix_sudo_command(check.name, check.fix)

    return FixResult(check.name, False, f"Manual action required: {check.fix}")
