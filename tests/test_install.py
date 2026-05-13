"""Tests for the install module."""
from __future__ import annotations

import io
import os
from unittest.mock import MagicMock, call, patch

import pytest
from rich.console import Console

from rocmate import install


# ---------------------------------------------------------------------------
# build_plan
# ---------------------------------------------------------------------------

def test_plan_tool_and_chip_set():
    plan = install.build_plan("ollama", "gfx1100")
    assert plan.tool == "ollama"
    assert plan.chip == "gfx1100"


def test_plan_tool_name_from_config():
    plan = install.build_plan("ollama", "gfx1100")
    assert plan.tool_name == "Ollama"


def test_plan_includes_env_vars():
    plan = install.build_plan("comfyui", "gfx1100")
    assert "HSA_OVERRIDE_GFX_VERSION" in plan.env_vars
    assert "PYTORCH_HIP_ALLOC_CONF" in plan.env_vars


def test_plan_no_env_vars_for_ollama_gfx1100():
    plan = install.build_plan("ollama", "gfx1100")
    assert plan.env_vars == {}


def test_plan_extracts_pip_commands():
    plan = install.build_plan("comfyui", "gfx1100")
    assert any("pip install" in cmd for cmd in plan.commands)


def test_plan_extracts_git_commands():
    plan = install.build_plan("llama-cpp", "gfx1100")
    assert any(cmd.startswith("cmake") for cmd in plan.commands)


def test_plan_raises_for_unknown_tool():
    with pytest.raises(FileNotFoundError):
        install.build_plan("nonexistent-tool", "gfx1100")


def test_plan_raises_for_unknown_chip():
    with pytest.raises(KeyError):
        install.build_plan("ollama", "gfx9999")


def test_plan_hints_contain_informational_lines():
    plan = install.build_plan("ollama", "gfx1100")
    # install_hints contains lines like "Windows: ..." and "Verify with: ..."
    assert any(plan.hints)


def test_commands_do_not_contain_informational_lines():
    plan = install.build_plan("ollama", "gfx1100")
    for cmd in plan.commands:
        assert not cmd.startswith("Windows:"), f"Informational hint in commands: {cmd}"
        assert not cmd.startswith("Verify"), f"Informational hint in commands: {cmd}"


# ---------------------------------------------------------------------------
# render_dry_run
# ---------------------------------------------------------------------------

def _render_dry_run(plan: install.InstallPlan) -> str:
    buf = io.StringIO()
    console = Console(file=buf, highlight=False, no_color=True)
    install.render_dry_run(plan, console)
    return buf.getvalue()


def test_dry_run_shows_tool_name():
    plan = install.build_plan("ollama", "gfx1100")
    assert "ollama" in _render_dry_run(plan).lower()


def test_dry_run_shows_chip():
    plan = install.build_plan("ollama", "gfx1100")
    assert "gfx1100" in _render_dry_run(plan)


def test_dry_run_shows_env_vars():
    plan = install.build_plan("comfyui", "gfx1100")
    output = _render_dry_run(plan)
    assert "HSA_OVERRIDE_GFX_VERSION" in output
    assert "PYTORCH_HIP_ALLOC_CONF" in output


def test_dry_run_shows_commands():
    plan = install.build_plan("comfyui", "gfx1100")
    output = _render_dry_run(plan)
    assert "pip install" in output


def test_dry_run_indicates_it_is_dry_run():
    plan = install.build_plan("ollama", "gfx1100")
    output = _render_dry_run(plan)
    assert "dry" in output.lower() or "--yes" in output


# ---------------------------------------------------------------------------
# render_docker_compose
# ---------------------------------------------------------------------------

def test_docker_compose_has_services_key():
    plan = install.build_plan("comfyui", "gfx1100")
    snippet = install.render_docker_compose(plan)
    assert "services:" in snippet


def test_docker_compose_includes_env_vars():
    plan = install.build_plan("comfyui", "gfx1100")
    snippet = install.render_docker_compose(plan)
    assert "HSA_OVERRIDE_GFX_VERSION" in snippet


def test_docker_compose_includes_kfd_device():
    plan = install.build_plan("comfyui", "gfx1100")
    snippet = install.render_docker_compose(plan)
    assert "/dev/kfd" in snippet


def test_docker_compose_includes_tool_as_service_name():
    plan = install.build_plan("comfyui", "gfx1100")
    snippet = install.render_docker_compose(plan)
    assert "comfyui" in snippet


# ---------------------------------------------------------------------------
# execute (--yes mode)
# ---------------------------------------------------------------------------

def test_execute_sets_env_vars():
    plan = install.build_plan("comfyui", "gfx1100")
    with patch("rocmate.install.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        with patch.dict(os.environ, {}, clear=False):
            install.execute(plan)
            assert os.environ.get("HSA_OVERRIDE_GFX_VERSION") == "11.0.0"


def test_execute_runs_commands():
    plan = install.build_plan("comfyui", "gfx1100")
    with patch("rocmate.install.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        install.execute(plan)
    assert mock_run.called


def test_execute_restores_env_on_failure():
    plan = install.build_plan("comfyui", "gfx1100")
    original = os.environ.get("HSA_OVERRIDE_GFX_VERSION")
    with patch("rocmate.install.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        with pytest.raises(install.InstallError):
            install.execute(plan)
    assert os.environ.get("HSA_OVERRIDE_GFX_VERSION") == original


def test_execute_no_commands_does_not_call_subprocess():
    plan = install.build_plan("ollama", "gfx1100")
    plan_no_cmds = install.InstallPlan(
        tool=plan.tool, chip=plan.chip, tool_name=plan.tool_name,
        env_vars={}, commands=[], hints=[],
    )
    with patch("rocmate.install.subprocess.run") as mock_run:
        install.execute(plan_no_cmds)
    mock_run.assert_not_called()
