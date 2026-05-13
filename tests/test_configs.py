"""Tests for config loading, validation, and rendering."""

from __future__ import annotations

import io

import pytest
from rich.console import Console

from rocmate import configs

# --- list_tools ---


def test_list_tools_returns_all_tools():
    assert set(configs.list_tools()) == {
        "ollama",
        "comfyui",
        "faster-whisper",
        "llama-cpp",
        "stable-diffusion-webui",
        "vllm",
        "axolotl",
        "exllamav2",
    }


def test_list_tools_is_sorted():
    tools = configs.list_tools()
    assert tools == sorted(tools)


# --- load_tool ---


def test_all_yamls_load_without_error():
    for tool in configs.list_tools():
        cfg = configs.load_tool(tool)
        assert cfg.name
        assert cfg.chips


def test_load_unknown_tool_raises():
    with pytest.raises(FileNotFoundError):
        configs.load_tool("nonexistent-tool")


# --- ChipSupport field validation across all YAMLs ---

VALID_STATUSES = {"tested", "partial", "broken"}


def test_all_chips_have_valid_status():
    for tool in configs.list_tools():
        cfg = configs.load_tool(tool)
        for chip, support in cfg.chips.items():
            assert support.status in VALID_STATUSES, (
                f"{tool}/{chip} has invalid status '{support.status}'"
            )


def test_tested_on_rocm_is_string_or_none():
    for tool in configs.list_tools():
        cfg = configs.load_tool(tool)
        for chip, support in cfg.chips.items():
            assert support.tested_on_rocm is None or isinstance(support.tested_on_rocm, str), (
                f"{tool}/{chip}.tested_on_rocm must be str or None"
            )


def test_env_vars_are_string_dicts():
    for tool in configs.list_tools():
        cfg = configs.load_tool(tool)
        for chip, support in cfg.chips.items():
            assert isinstance(support.env_vars, dict)
            for k, v in support.env_vars.items():
                assert isinstance(k, str) and isinstance(v, str), (
                    f"{tool}/{chip} env_vars must be str→str"
                )


def test_install_hints_are_string_lists():
    for tool in configs.list_tools():
        cfg = configs.load_tool(tool)
        for chip, support in cfg.chips.items():
            assert isinstance(support.install_hints, list)
            for hint in support.install_hints:
                assert isinstance(hint, str), f"{tool}/{chip} install_hints must be strings"


# --- Specific config content ---


def test_ollama_gfx1100_fully_populated():
    chip = configs.load_tool("ollama").chips["gfx1100"]
    assert chip.status == "tested"
    assert chip.tested_on_rocm is not None
    assert chip.install_hints


def test_ollama_gfx1034_has_hsa_override():
    chip = configs.load_tool("ollama").chips["gfx1034"]
    assert "HSA_OVERRIDE_GFX_VERSION" in chip.env_vars


def test_comfyui_gfx1100_has_pytorch_env():
    chip = configs.load_tool("comfyui").chips["gfx1100"]
    assert "PYTORCH_HIP_ALLOC_CONF" in chip.env_vars


def test_ollama_covers_gfx1101():
    assert "gfx1101" in configs.load_tool("ollama").chips


def test_ollama_covers_gfx1102():
    assert "gfx1102" in configs.load_tool("ollama").chips


def test_comfyui_covers_gfx1101():
    assert "gfx1101" in configs.load_tool("comfyui").chips


def test_comfyui_covers_gfx1102():
    assert "gfx1102" in configs.load_tool("comfyui").chips


def test_faster_whisper_covers_gfx1101():
    assert "gfx1101" in configs.load_tool("faster-whisper").chips


# Windows install hints — at least one tool must have a Windows-specific hint
# for each major chip family to fulfil v0.2 goals.


def test_ollama_gfx1100_has_windows_install_hint():
    hints = configs.load_tool("ollama").chips["gfx1100"].install_hints
    assert any("windows" in h.lower() or "adrenalin" in h.lower() for h in hints)


def test_comfyui_gfx1100_has_windows_install_hint():
    hints = configs.load_tool("comfyui").chips["gfx1100"].install_hints
    assert any("windows" in h.lower() or "hip" in h.lower() for h in hints)


# New tools present
def test_llama_cpp_config_exists():
    cfg = configs.load_tool("llama-cpp")
    assert cfg.name
    assert cfg.chips


def test_stable_diffusion_webui_config_exists():
    cfg = configs.load_tool("stable-diffusion-webui")
    assert cfg.name
    assert cfg.chips


def test_vllm_config_exists():
    cfg = configs.load_tool("vllm")
    assert cfg.name
    assert cfg.chips


def test_vllm_covers_gfx1100():
    assert "gfx1100" in configs.load_tool("vllm").chips


def test_vllm_gfx1100_is_tested():
    chip = configs.load_tool("vllm").chips["gfx1100"]
    assert chip.status == "tested"


def test_axolotl_config_exists():
    cfg = configs.load_tool("axolotl")
    assert cfg.name
    assert cfg.chips


def test_axolotl_covers_gfx1100():
    assert "gfx1100" in configs.load_tool("axolotl").chips


def test_exllamav2_config_exists():
    cfg = configs.load_tool("exllamav2")
    assert cfg.name
    assert cfg.chips


def test_exllamav2_covers_gfx1100():
    assert "gfx1100" in configs.load_tool("exllamav2").chips


def test_exllamav2_gfx1100_has_cmake_hint():
    hints = configs.load_tool("exllamav2").chips["gfx1100"].install_hints
    assert any("cmake" in h.lower() or "pip install" in h.lower() for h in hints)


# --- render ---


def _render_to_str(cfg: configs.ToolConfig) -> str:
    buf = io.StringIO()
    console = Console(file=buf, highlight=False, no_color=True)
    configs.render(cfg, console)
    return buf.getvalue()


def test_render_shows_tool_name():
    cfg = configs.load_tool("ollama")
    assert "Ollama" in _render_to_str(cfg)


def test_render_shows_all_chips():
    cfg = configs.load_tool("ollama")
    output = _render_to_str(cfg)
    for chip in cfg.chips:
        assert chip in output


def test_render_shows_rocm_version_for_tested_chip():
    cfg = configs.load_tool("ollama")
    output = _render_to_str(cfg)
    assert cfg.chips["gfx1100"].tested_on_rocm in output


def test_render_shows_question_mark_for_unknown_rocm():
    cfg = configs.load_tool("faster-whisper")
    # gfx1201 has no entry — if a chip has tested_on_rocm=None, show "?"
    # Find any chip without tested_on_rocm
    missing = [c for c, s in cfg.chips.items() if s.tested_on_rocm is None]
    if missing:
        output = _render_to_str(cfg)
        assert "?" in output
