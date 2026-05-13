"""Tool installation planner and executor."""

from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass, field

from rich.console import Console
from rich.panel import Panel

from rocmate import configs


class InstallError(RuntimeError):
    """Raised when a command exits non-zero during install."""


# Hints that start with these words are executable shell commands.
_EXECUTABLE_PREFIXES = (
    "pip ",
    "pip3 ",
    "git ",
    "cmake ",
    "curl ",
    "python ",
    "python3 ",
    "sudo ",
    "./",
    "docker ",
    "export ",
)


def _is_executable(hint: str) -> bool:
    stripped = hint.strip()
    if "&&" in stripped:
        return False
    return any(stripped.startswith(p) for p in _EXECUTABLE_PREFIXES)


@dataclass
class InstallPlan:
    tool: str
    chip: str
    tool_name: str
    env_vars: dict[str, str] = field(default_factory=dict)
    commands: list[str] = field(default_factory=list)
    hints: list[str] = field(default_factory=list)


def build_plan(tool: str, chip: str) -> InstallPlan:
    """Build an install plan for *tool* on *chip*.

    Raises FileNotFoundError if the tool config doesn't exist.
    Raises KeyError if the chip has no entry in the tool config.
    """
    cfg = configs.load_tool(tool)
    if chip not in cfg.chips:
        raise KeyError(f"No config for chip '{chip}' in tool '{tool}'")
    support = cfg.chips[chip]

    commands, hints = [], []
    for h in support.install_hints:
        (commands if _is_executable(h) else hints).append(h)

    return InstallPlan(
        tool=tool,
        chip=chip,
        tool_name=cfg.name,
        env_vars=dict(support.env_vars),
        commands=commands,
        hints=hints,
    )


def render_dry_run(plan: InstallPlan, console: Console) -> None:
    """Print what the install would do without executing anything."""
    console.print(
        Panel(
            f"[bold]{plan.tool_name}[/bold] on [bold]{plan.chip}[/bold]  [dim](dry-run)[/dim]",
            expand=False,
        )
    )

    if plan.env_vars:
        console.print("\n[bold]ENV vars:[/bold]")
        for k, v in plan.env_vars.items():
            console.print(f"  [cyan]export {k}={v}[/cyan]")

    if plan.commands:
        console.print("\n[bold]Commands:[/bold]")
        for cmd in plan.commands:
            console.print(f"  [dim]$[/dim] {cmd}")

    if plan.hints:
        console.print("\n[bold]Notes:[/bold]")
        for hint in plan.hints:
            console.print(f"  • {hint}")

    console.print("\n[dim]dry-run — confirm the prompt below to install.[/dim]")


def render_docker_compose(plan: InstallPlan) -> str:
    """Return a Docker Compose YAML snippet for the given plan."""
    env_lines = "\n".join(f"      - {k}={v}" for k, v in plan.env_vars.items())
    env_section = f"\n    environment:\n{env_lines}" if env_lines else ""

    return (
        f"services:\n"
        f"  {plan.tool}:\n"
        f"    image: {plan.tool}  # replace with an actual image\n"
        f"    devices:\n"
        f"      - /dev/kfd\n"
        f"      - /dev/dri\n"
        f"    group_add:\n"
        f"      - render\n"
        f"      - video\n"
        f"{env_section}\n"
    )


def execute(plan: InstallPlan) -> None:
    """Apply ENV vars and run commands.

    Restores ENV vars to their original values if any command fails.
    Raises InstallError on non-zero exit.
    """
    # Snapshot current values for rollback
    snapshot: dict[str, str | None] = {k: os.environ.get(k) for k in plan.env_vars}

    # Apply ENV vars
    for k, v in plan.env_vars.items():
        os.environ[k] = v

    try:
        for cmd in plan.commands:
            result = subprocess.run(shlex.split(cmd), shell=False, check=False)
            if result.returncode != 0:
                raise InstallError(f"Command failed (exit {result.returncode}): {cmd}")
    except InstallError:
        # Restore ENV vars
        for k, original in snapshot.items():
            if original is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = original
        raise
