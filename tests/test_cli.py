"""Tests for CLI commands."""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from rocmate.cli import app
from rocmate.doctor import CheckResult, Status
from rocmate.fixer import FixResult
from rocmate.gpu import GpuInfo

runner = CliRunner()


# --- rocmate --version ---


def test_version_flag_exits_zero():
    assert runner.invoke(app, ["--version"]).exit_code == 0


def test_version_flag_shows_version_number():
    result = runner.invoke(app, ["--version"])
    assert "0." in result.output


def test_version_flag_shows_rocmate():
    result = runner.invoke(app, ["--version"])
    assert "rocmate" in result.output.lower()


# --- rocmate list ---


def test_list_exits_zero():
    assert runner.invoke(app, ["list"]).exit_code == 0


def test_list_shows_all_tools():
    result = runner.invoke(app, ["list"])
    assert "ollama" in result.output
    assert "comfyui" in result.output
    assert "faster-whisper" in result.output


def test_list_shows_tool_count():
    result = runner.invoke(app, ["list"])
    assert "8" in result.output


# --- rocmate show ---


def test_show_exits_zero_for_known_tool():
    assert runner.invoke(app, ["show", "ollama"]).exit_code == 0


def test_show_displays_tool_name():
    result = runner.invoke(app, ["show", "ollama"])
    assert "Ollama" in result.output


def test_show_displays_chip_data():
    result = runner.invoke(app, ["show", "ollama"])
    assert "gfx1100" in result.output


def test_show_displays_rocm_version():
    result = runner.invoke(app, ["show", "ollama"])
    assert "6.3" in result.output


def test_show_exits_nonzero_for_unknown_tool():
    result = runner.invoke(app, ["show", "does-not-exist"])
    assert result.exit_code != 0


def test_show_chip_filter_shows_only_that_chip():
    result = runner.invoke(app, ["show", "ollama", "--chip", "gfx1100"])
    assert "gfx1100" in result.output
    assert "gfx1030" not in result.output


def test_show_chip_filter_exits_nonzero_for_unknown_chip():
    result = runner.invoke(app, ["show", "ollama", "--chip", "gfx9999"])
    assert result.exit_code != 0


# --- rocmate search ---


def test_search_exits_zero():
    assert runner.invoke(app, ["search", "llm"]).exit_code == 0


def test_search_finds_ollama_by_keyword():
    result = runner.invoke(app, ["search", "ollama"])
    assert "ollama" in result.output.lower()


def test_search_finds_by_description_keyword():
    result = runner.invoke(app, ["search", "whisper"])
    assert "faster-whisper" in result.output.lower()


def test_search_no_results_exits_nonzero():
    result = runner.invoke(app, ["search", "zzznomatch"])
    assert result.exit_code != 0


def test_show_unknown_tool_suggests_available():
    result = runner.invoke(app, ["show", "does-not-exist"])
    assert "ollama" in result.output.lower()


# --- rocmate doctor ---


def test_doctor_exits_one_without_rocm():
    with (
        patch("rocmate.gpu.detect_amd_gpus", return_value=[]),
        patch("rocmate.gpu.get_rocm_version", return_value=None),
    ):
        result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1


def test_doctor_produces_output():
    result = runner.invoke(app, ["doctor"])
    assert len(result.output) > 0


def test_doctor_exits_zero_when_system_ok():
    gpu = GpuInfo("RX 7900 XTX", "gfx1100", 24576)
    with (
        patch("rocmate.gpu.detect_amd_gpus", return_value=[gpu]),
        patch("rocmate.gpu.get_rocm_version", return_value="6.3.1"),
        patch("rocmate.doctor._check_groups", return_value=[]),
    ):
        result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0


# --- rocmate install ---


class TestInstallCommand:
    def _with_gpu(self, args: list[str], input: str = "n\n") -> object:
        from rocmate.gpu import GpuInfo

        gpu = GpuInfo("RX 7900 XTX", "gfx1100", 24576)
        with patch("rocmate.gpu.detect_amd_gpus", return_value=[gpu]):
            return runner.invoke(app, args, input=input)

    def test_install_shows_plan_before_prompt(self):
        result = self._with_gpu(["install", "ollama"])
        assert "ollama" in result.output.lower()

    def test_install_shows_confirmation_prompt(self):
        result = self._with_gpu(["install", "ollama"])
        assert "install" in result.output.lower() or "[y" in result.output.lower()

    def test_install_declined_exits_zero(self):
        result = self._with_gpu(["install", "ollama"], input="n\n")
        assert result.exit_code == 0

    def test_install_unknown_tool_exits_nonzero(self):
        result = self._with_gpu(["install", "nonexistent-tool"])
        assert result.exit_code != 0

    def test_install_no_gpu_exits_nonzero(self):
        with patch("rocmate.gpu.detect_amd_gpus", return_value=[]):
            result = runner.invoke(app, ["install", "ollama"])
        assert result.exit_code != 0

    def test_install_docker_flag_shows_compose(self):
        result = self._with_gpu(["install", "comfyui", "--docker"])
        assert "services:" in result.output
        assert "/dev/kfd" in result.output

    def test_install_confirmed_calls_execute(self):
        with patch("rocmate.install.execute") as mock_exec:
            self._with_gpu(["install", "ollama"], input="y\n")
        mock_exec.assert_called_once()

    def test_install_declined_does_not_call_execute(self):
        with patch("rocmate.install.execute") as mock_exec:
            self._with_gpu(["install", "ollama"], input="n\n")
        mock_exec.assert_not_called()


def test_doctor_shows_gpu_name_when_detected():
    gpu = GpuInfo("RX 7900 XTX", "gfx1100", 24576)
    with (
        patch("rocmate.gpu.detect_amd_gpus", return_value=[gpu]),
        patch("rocmate.gpu.get_rocm_version", return_value="6.3.1"),
        patch("rocmate.doctor._check_groups", return_value=[]),
    ):
        result = runner.invoke(app, ["doctor"])
    assert "RX 7900 XTX" in result.output


# --- rocmate doctor --tool ---


class TestDoctorToolFlag:
    def _doctor_with_gpu(self, args: list[str]) -> object:
        gpu = GpuInfo("RX 7900 XTX", "gfx1100", 24576)
        with (
            patch("rocmate.gpu.detect_amd_gpus", return_value=[gpu]),
            patch("rocmate.gpu.get_rocm_version", return_value="6.3.1"),
            patch("rocmate.doctor._check_groups", return_value=[]),
        ):
            return runner.invoke(app, args)

    def test_doctor_tool_exits_zero_for_known_tool(self):
        result = self._doctor_with_gpu(["doctor", "--tool", "ollama"])
        assert result.exit_code == 0

    def test_doctor_tool_shows_tool_name(self):
        result = self._doctor_with_gpu(["doctor", "--tool", "ollama"])
        assert "ollama" in result.output.lower()

    def test_doctor_tool_shows_chip_compatibility(self):
        result = self._doctor_with_gpu(["doctor", "--tool", "ollama"])
        assert "gfx1100" in result.output

    def test_doctor_tool_exits_nonzero_for_unknown_tool(self):
        result = self._doctor_with_gpu(["doctor", "--tool", "nonexistent"])
        assert result.exit_code != 0

    def test_doctor_tool_shows_status_for_detected_chip(self):
        result = self._doctor_with_gpu(["doctor", "--tool", "ollama"])
        assert "tested" in result.output.lower()

    def test_doctor_tool_warns_when_no_gpu_detected(self):
        with (
            patch("rocmate.gpu.detect_amd_gpus", return_value=[]),
            patch("rocmate.gpu.get_rocm_version", return_value=None),
        ):
            result = runner.invoke(app, ["doctor", "--tool", "ollama"])
        assert result.exit_code != 0


# --- rocmate doctor --fix ---


class TestDoctorFixFlag:
    def _all_ok(self, args: list[str], input: str = "") -> object:
        gpu = GpuInfo("RX 7900 XTX", "gfx1100", 24576)
        with (
            patch("rocmate.gpu.detect_amd_gpus", return_value=[gpu]),
            patch("rocmate.gpu.get_rocm_version", return_value="6.3.1"),
            patch("rocmate.doctor._check_groups", return_value=[]),
            patch("rocmate.doctor._check_docker", return_value=[]),
            patch("rocmate.doctor._check_vulkan", return_value=[]),
        ):
            return runner.invoke(app, args, input=input)

    def _with_fixable_check(self, args: list[str], input: str = "n\n") -> object:
        gpu = GpuInfo("RX 7900 XTX", "gfx1100", 24576)
        warn_check = CheckResult(
            "env:HSA_OVERRIDE_GFX_VERSION",
            Status.WARN,
            "HSA_OVERRIDE_GFX_VERSION not set",
            fix="export HSA_OVERRIDE_GFX_VERSION=10.3.0",
        )
        with (
            patch("rocmate.gpu.detect_amd_gpus", return_value=[gpu]),
            patch("rocmate.gpu.get_rocm_version", return_value="6.3.1"),
            patch("rocmate.doctor._check_groups", return_value=[]),
            patch("rocmate.doctor._check_docker", return_value=[]),
            patch("rocmate.doctor._check_vulkan", return_value=[warn_check]),
        ):
            return runner.invoke(app, args, input=input)

    def test_fix_flag_shows_nothing_to_fix_when_all_ok(self):
        result = self._all_ok(["doctor", "--fix"])
        assert "nothing to fix" in result.output.lower()

    def test_fix_flag_exits_zero_when_all_ok(self):
        result = self._all_ok(["doctor", "--fix"])
        assert result.exit_code == 0

    def test_fix_flag_shows_fix_description(self):
        result = self._with_fixable_check(["doctor", "--fix"])
        assert "HSA_OVERRIDE" in result.output

    def test_fix_flag_calls_apply_fix_when_confirmed(self):
        with patch("rocmate.fixer.apply_fix") as mock_apply:
            mock_apply.return_value = FixResult(
                "env:HSA_OVERRIDE_GFX_VERSION", True, "Added to ~/.bashrc"
            )
            self._with_fixable_check(["doctor", "--fix"], input="y\n")
        mock_apply.assert_called_once()

    def test_fix_flag_does_not_call_apply_fix_when_declined(self):
        with patch("rocmate.fixer.apply_fix") as mock_apply:
            self._with_fixable_check(["doctor", "--fix"], input="n\n")
        mock_apply.assert_not_called()

    def test_fix_flag_shows_success_after_apply(self):
        with patch("rocmate.fixer.apply_fix") as mock_apply:
            mock_apply.return_value = FixResult(
                "env:HSA_OVERRIDE_GFX_VERSION", True, "Added to ~/.bashrc"
            )
            result = self._with_fixable_check(["doctor", "--fix"], input="y\n")
        assert "bashrc" in result.output.lower() or "added" in result.output.lower()


# --- rocmate list --chip ---


def test_list_chip_filter_exits_zero():
    assert runner.invoke(app, ["list", "--chip", "gfx1100"]).exit_code == 0


def test_list_chip_filter_shows_only_supported_tools():
    result = runner.invoke(app, ["list", "--chip", "gfx1100"])
    assert "ollama" in result.output.lower()


def test_list_chip_filter_excludes_unsupported_tools():
    # faster-whisper has no gfx1201 entry
    result = runner.invoke(app, ["list", "--chip", "gfx1201"])
    assert "faster-whisper" not in result.output.lower()


def test_list_chip_filter_exits_nonzero_for_no_matches():
    result = runner.invoke(app, ["list", "--chip", "gfx9999"])
    assert result.exit_code != 0


def test_list_chip_filter_shows_chip_in_output():
    result = runner.invoke(app, ["list", "--chip", "gfx1100"])
    assert "gfx1100" in result.output


# --- rocmate install --chip ---


class TestInstallChipFlag:
    def test_install_chip_flag_bypasses_gpu_detection(self):
        with patch("rocmate.gpu.detect_amd_gpus", return_value=[]):
            result = runner.invoke(app, ["install", "ollama", "--chip", "gfx1100"], input="n\n")
        assert result.exit_code == 0

    def test_install_chip_flag_shows_plan_for_given_chip(self):
        with patch("rocmate.gpu.detect_amd_gpus", return_value=[]):
            result = runner.invoke(app, ["install", "ollama", "--chip", "gfx1100"], input="n\n")
        assert "gfx1100" in result.output

    def test_install_chip_flag_exits_nonzero_for_unknown_chip(self):
        with patch("rocmate.gpu.detect_amd_gpus", return_value=[]):
            result = runner.invoke(app, ["install", "ollama", "--chip", "gfx9999"])
        assert result.exit_code != 0

    def test_install_chip_flag_takes_precedence_over_detected_gpu(self):
        gpu = GpuInfo("RX 7900 XTX", "gfx1100", 24576)
        with patch("rocmate.gpu.detect_amd_gpus", return_value=[gpu]):
            result = runner.invoke(app, ["install", "ollama", "--chip", "gfx1030"], input="n\n")
        assert "gfx1030" in result.output


# --- rocmate show: export lines ---


def test_show_env_vars_as_export_lines():
    result = runner.invoke(app, ["show", "comfyui"])
    assert "export HSA_OVERRIDE_GFX_VERSION" in result.output


def test_show_chip_env_vars_as_export_lines():
    result = runner.invoke(app, ["show", "comfyui", "--chip", "gfx1100"])
    assert "export HSA_OVERRIDE_GFX_VERSION" in result.output
