"""Tests for the fixer module."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rocmate import fixer
from rocmate.doctor import CheckResult, Status


# --- classify_fix ---

def test_classify_export_returns_env_profile():
    assert fixer.classify_fix("export HSA_OVERRIDE_GFX_VERSION=10.3.0") == fixer.FixKind.ENV_PROFILE


def test_classify_sudo_returns_sudo_command():
    assert fixer.classify_fix("sudo usermod -aG render $USER && newgrp render") == fixer.FixKind.SUDO_COMMAND


def test_classify_url_returns_manual():
    assert fixer.classify_fix("Install ROCm: https://rocm.docs.amd.com") == fixer.FixKind.MANUAL


def test_classify_apt_returns_sudo_command():
    assert fixer.classify_fix("sudo apt install mesa-vulkan-drivers") == fixer.FixKind.SUDO_COMMAND


def test_classify_instruction_returns_manual():
    assert fixer.classify_fix("Ensure /dev/kfd and /dev/dri are passed to containers") == fixer.FixKind.MANUAL


# --- _detect_shell_profile ---

def test_detect_shell_profile_returns_zshrc_for_zsh(tmp_path):
    with patch.dict(os.environ, {"SHELL": "/bin/zsh"}), \
         patch("rocmate.fixer.Path") as mock_path:
        mock_path.home.return_value = tmp_path
        result = fixer._detect_shell_profile()
    assert result == tmp_path / ".zshrc"


def test_detect_shell_profile_returns_bashrc_as_default(tmp_path):
    with patch.dict(os.environ, {"SHELL": "/bin/bash"}), \
         patch("rocmate.fixer.Path") as mock_path:
        mock_path.home.return_value = tmp_path
        result = fixer._detect_shell_profile()
    assert result == tmp_path / ".bashrc"


# --- fix_env_in_profile ---

def test_fix_env_writes_export_line(tmp_path):
    profile = tmp_path / ".bashrc"
    with patch("rocmate.fixer._detect_shell_profile", return_value=profile):
        result = fixer.fix_env_in_profile("MY_VAR", "my_value")
    assert result.applied
    assert "export MY_VAR=my_value" in profile.read_text()


def test_fix_env_appends_rocmate_comment(tmp_path):
    profile = tmp_path / ".bashrc"
    with patch("rocmate.fixer._detect_shell_profile", return_value=profile):
        fixer.fix_env_in_profile("MY_VAR", "my_value")
    assert "rocmate" in profile.read_text().lower()


def test_fix_env_is_idempotent(tmp_path):
    profile = tmp_path / ".bashrc"
    profile.write_text("export MY_VAR=my_value\n")
    with patch("rocmate.fixer._detect_shell_profile", return_value=profile):
        result = fixer.fix_env_in_profile("MY_VAR", "my_value")
    assert not result.applied


def test_fix_env_preserves_existing_content(tmp_path):
    profile = tmp_path / ".bashrc"
    profile.write_text("# existing content\nexport PATH=$PATH:/usr/local/bin\n")
    with patch("rocmate.fixer._detect_shell_profile", return_value=profile):
        fixer.fix_env_in_profile("NEW_VAR", "new_value")
    content = profile.read_text()
    assert "existing content" in content
    assert "export NEW_VAR=new_value" in content


# --- fix_sudo_command ---

def test_fix_sudo_command_success():
    with patch("rocmate.fixer.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = fixer.fix_sudo_command("group:render", "sudo usermod -aG render testuser")
    assert result.applied


def test_fix_sudo_command_failure():
    with patch("rocmate.fixer.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        result = fixer.fix_sudo_command("group:render", "sudo usermod -aG render testuser")
    assert not result.applied


def test_fix_sudo_command_strips_compound_at_double_ampersand():
    with patch("rocmate.fixer.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        fixer.fix_sudo_command("group:render", "sudo usermod -aG render $USER && newgrp render")
    called_cmd = mock_run.call_args[0][0]
    assert "&&" not in called_cmd
    assert "usermod" in called_cmd


# --- apply_fix ---

def test_apply_fix_returns_none_for_no_fix():
    check = CheckResult("gpu", Status.FAIL, "No GPU detected")
    assert fixer.apply_fix(check) is None


def test_apply_fix_env_export_writes_profile(tmp_path):
    check = CheckResult(
        "env:HSA_OVERRIDE_GFX_VERSION", Status.WARN,
        "HSA_OVERRIDE_GFX_VERSION not set",
        fix="export HSA_OVERRIDE_GFX_VERSION=10.3.0",
    )
    profile = tmp_path / ".bashrc"
    with patch("rocmate.fixer._detect_shell_profile", return_value=profile):
        result = fixer.apply_fix(check)
    assert result is not None
    assert result.applied
    assert "HSA_OVERRIDE_GFX_VERSION" in profile.read_text()


def test_apply_fix_sudo_runs_command():
    check = CheckResult(
        "group:render", Status.FAIL, "Not in render group",
        fix="sudo usermod -aG render $USER && newgrp render",
    )
    with patch("rocmate.fixer.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = fixer.apply_fix(check)
    assert result is not None
    assert result.applied


def test_apply_fix_manual_returns_not_applied():
    check = CheckResult(
        "gpu", Status.FAIL, "No GPU",
        fix="Install ROCm: https://rocm.docs.amd.com",
    )
    result = fixer.apply_fix(check)
    assert result is not None
    assert not result.applied
