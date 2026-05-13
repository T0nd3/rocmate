"""Smoke tests for rocmate modules."""

from __future__ import annotations

from rocmate import configs


def test_list_tools_returns_nonempty() -> None:
    tools = configs.list_tools()
    assert "ollama" in tools
    assert "comfyui" in tools
    assert "faster-whisper" in tools


def test_load_ollama_config() -> None:
    cfg = configs.load_tool("ollama")
    assert cfg.name == "Ollama"
    assert "gfx1100" in cfg.chips
    assert cfg.chips["gfx1100"].status == "tested"


def test_load_unknown_tool_raises() -> None:
    import pytest

    with pytest.raises(FileNotFoundError):
        configs.load_tool("nonexistent-tool")


def test_doctor_runs_without_crashing() -> None:
    """Doctor should not crash even on a system without ROCm."""
    from rocmate import doctor

    report = doctor.run()
    assert isinstance(report.checks, list)
    assert len(report.checks) > 0
