"""Tool configuration loading and rendering."""
from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


class ChipSupport(BaseModel):
    status: str  # "tested" | "partial" | "broken"
    tested_on_rocm: Optional[str] = None  # e.g. "6.2", "6.3" — None = unknown
    notes: Optional[str] = None
    env_vars: dict[str, str] = Field(default_factory=dict)
    install_hints: list[str] = Field(default_factory=list)


class ToolConfig(BaseModel):
    name: str
    description: str
    homepage: Optional[str] = None
    chips: dict[str, ChipSupport] = Field(default_factory=dict)


def _configs_dir() -> Path:
    """Locate the bundled configs directory."""
    # Dev mode: configs/ next to src/ (repo checkout)
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "configs" / "tools"
        if candidate.is_dir():
            return candidate
    # Installed: configs live under rocmate/_configs (via hatch force-include)
    try:
        installed = Path(str(files("rocmate").joinpath("_configs/tools")))
        if installed.is_dir():
            return installed
    except (ModuleNotFoundError, FileNotFoundError):
        pass
    raise FileNotFoundError("Could not locate rocmate configs directory")


def list_tools() -> list[str]:
    return sorted(p.stem for p in _configs_dir().glob("*.yaml"))


def load_tool(tool: str) -> ToolConfig:
    path = _configs_dir() / f"{tool}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"No config for tool '{tool}'")
    data = yaml.safe_load(path.read_text())
    return ToolConfig(**data)


_STATUS_STYLE = {
    "tested": "[green]✅ tested[/green]",
    "partial": "[yellow]🟡 partial[/yellow]",
    "broken": "[red]❌ broken[/red]",
}


def render(config: ToolConfig, console: Console) -> None:
    header = f"[bold]{config.name}[/bold]\n{config.description}"
    if config.homepage:
        header += f"\n[dim]{config.homepage}[/dim]"
    console.print(Panel(header, expand=False))

    table = Table(title="Chip support", show_lines=False)
    table.add_column("Chip")
    table.add_column("Status")
    table.add_column("ROCm")
    table.add_column("Notes")
    for chip, support in config.chips.items():
        table.add_row(
            chip,
            _STATUS_STYLE.get(support.status, support.status),
            support.tested_on_rocm or "[dim]?[/dim]",
            support.notes or "",
        )
    console.print(table)

    for chip, support in config.chips.items():
        if not support.env_vars and not support.install_hints:
            continue
        console.print(f"\n[bold]{chip}[/bold]")
        if support.env_vars:
            console.print("  Environment:")
            for k, v in support.env_vars.items():
                console.print(f"    [cyan]export {k}={v}[/cyan]")
        if support.install_hints:
            console.print("  Install hints:")
            for hint in support.install_hints:
                console.print(f"    • {hint}")
