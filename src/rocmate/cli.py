"""rocmate command-line interface."""
from __future__ import annotations

import typer
from rich.console import Console

from rocmate import configs as configs_module
from rocmate import doctor as doctor_module
from rocmate import fixer as fixer_module
from rocmate import install as install_module
from rocmate.doctor import Status
from rocmate.install import InstallError

app = typer.Typer(
    name="rocmate",
    help="Curated AMD GPU compatibility index and CLI for AI workloads.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()

_STATUS_ICON = {
    "tested": "[green]✅ tested[/green]",
    "partial": "[yellow]\U0001f7e1 partial[/yellow]",
    "broken": "[red]❌ broken[/red]",
}


@app.command()
def doctor(
    tool: str | None = typer.Option(
        None, "--tool", help="Also show compatibility for a specific tool."
    ),
    fix: bool = typer.Option(
        False, "--fix", help="Interactively apply fixes for detected issues."
    ),
) -> None:
    """Check whether the system is ready for AI workloads on an AMD GPU."""
    result = doctor_module.run()
    doctor_module.render(result, console)

    if tool is not None:
        try:
            cfg = configs_module.load_tool(tool)
        except FileNotFoundError:
            console.print(f"[red]No config for tool '{tool}'.[/red]")
            console.print(f"Available tools: {', '.join(configs_module.list_tools())}")
            raise typer.Exit(code=1) from None

        console.print(f"\n[bold]Tool compatibility: {cfg.name}[/bold]")
        if not result.gpu_info:
            console.print(
                "[yellow]  No AMD GPU detected — cannot check tool compatibility.[/yellow]"
            )
        else:
            for gpu_info in result.gpu_info:
                chip = gpu_info.gfx_version
                if chip in cfg.chips:
                    support = cfg.chips[chip]
                    icon = _STATUS_ICON.get(support.status, support.status)
                    rocm = f" (ROCm {support.tested_on_rocm})" if support.tested_on_rocm else ""
                    console.print(f"  {chip}: {icon}{rocm}")
                else:
                    console.print(f"  {chip}: [dim]no data[/dim]")

    if fix:
        fixable = [c for c in result.checks if c.fix and c.status != Status.OK]
        if not fixable:
            console.print("[green]Nothing to fix.[/green]")
        else:
            for check in fixable:
                console.print(f"\n[bold]Fix available:[/bold] {check.name}")
                console.print(f"  [dim]{check.fix}[/dim]")
                if typer.confirm("Apply?", default=False):
                    fix_result = fixer_module.apply_fix(check)
                    if fix_result and fix_result.applied:
                        console.print(f"  [green]✓ {fix_result.message}[/green]")
                    elif fix_result:
                        console.print(f"  [yellow]⚠ {fix_result.message}[/yellow]")

    if result.has_blocking_issues():
        raise typer.Exit(code=1)


@app.command()
def show(tool: str = typer.Argument(..., help="Tool name, e.g. 'ollama'")) -> None:
    """Show the tested configuration for a given tool."""
    try:
        config = configs_module.load_tool(tool)
    except FileNotFoundError:
        console.print(f"[red]No config available for tool '{tool}'.[/red]")
        console.print(f"Available tools: {', '.join(configs_module.list_tools())}")
        raise typer.Exit(code=1) from None
    configs_module.render(config, console)


@app.command(name="list")
def list_tools() -> None:
    """List all tools with tested configurations."""
    tools = configs_module.list_tools()
    console.print(f"[bold]Available tools ({len(tools)}):[/bold]")
    for t in tools:
        console.print(f"  • {t}")


@app.command()
def install(
    tool: str = typer.Argument(..., help="Tool to install, e.g. 'ollama'"),
    docker: bool = typer.Option(False, "--docker", help="Print a Docker Compose snippet instead."),
) -> None:
    """Install a tool with the correct ENV vars and pip indexes for your AMD GPU."""
    from rocmate import gpu as gpu_module

    gpus = gpu_module.detect_amd_gpus()
    if not gpus:
        console.print("[red]No AMD GPU detected — cannot determine install config.[/red]")
        raise typer.Exit(code=1)

    chip = gpus[0].gfx_version
    try:
        plan = install_module.build_plan(tool, chip)
    except FileNotFoundError:
        console.print(f"[red]No config for tool '{tool}'.[/red]")
        console.print(f"Available tools: {', '.join(configs_module.list_tools())}")
        raise typer.Exit(code=1) from None
    except KeyError:
        console.print(f"[yellow]No install config for {chip} + {tool}.[/yellow]")
        raise typer.Exit(code=1) from None

    if docker:
        console.print(install_module.render_docker_compose(plan))
        return

    install_module.render_dry_run(plan, console)

    if typer.confirm("Install now?", default=False):
        try:
            install_module.execute(plan)
            console.print("[green]Done.[/green]")
        except InstallError as e:
            console.print(f"[red]Install failed:[/red] {e}")
            raise typer.Exit(code=1) from None


if __name__ == "__main__":
    app()
