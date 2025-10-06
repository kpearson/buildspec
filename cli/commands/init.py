"""Init command implementation."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from cli.core.config import Config

console = Console()


def command(
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing configuration"
    ),
    show_config: bool = typer.Option(
        False, "--show", help="Show default configuration without creating"
    ),
):
    """Initialize buildspec configuration (XDG-compliant).

    Creates ~/.config/buildspec/config.toml with default settings.
    Also creates additional XDG directories for templates, state, and cache.
    """
    config = Config()

    # Show config and exit
    if show_config:
        console.print("\n[bold]Default configuration:[/bold]\n")
        syntax = Syntax(
            Config.get_default_config(), "toml", theme="monokai", line_numbers=True
        )
        console.print(syntax)
        console.print(f"\n[dim]Would be created at: {config.config_file}[/dim]")
        return

    # Check if config exists
    if config.exists() and not force:
        console.print(
            Panel(
                f"[yellow]Configuration already exists:[/yellow]\n"
                f"{config.config_file}\n\n"
                f"Use [bold]--force[/bold] to overwrite or [bold]--show[/bold] to view default config",
                title="⚠️  Config Exists",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=1)

    try:
        # Remove existing if force
        if force and config.exists():
            config.config_file.unlink()
            console.print("[yellow]Removed existing config[/yellow]")

        # Create config file
        config_path = config.create_default()

        # Create XDG directories
        dirs = config.create_directories()

        # Success message
        console.print(
            Panel(
                f"[green]✓[/green] Configuration created: [bold]{config_path}[/bold]\n\n"
                f"[dim]XDG directories created:[/dim]\n"
                f"  • Config:    {dirs['config']}\n"
                f"  • Templates: {dirs['templates']}\n"
                f"  • State:     {dirs['state']}\n"
                f"  • Cache:     {dirs['cache']}\n\n"
                f"[dim]Edit the config file to customize buildspec behavior.[/dim]",
                title="✅ Buildspec Initialized",
                border_style="green",
            )
        )

        # Show config preview
        console.print("\n[bold]Configuration preview:[/bold]\n")
        syntax = Syntax(
            config.config_file.read_text(), "toml", theme="monokai", line_numbers=False
        )
        console.print(syntax)

    except FileExistsError as e:
        console.print(f"[red]ERROR:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]ERROR:[/red] Failed to create configuration: {e}")
        raise typer.Exit(code=1)
