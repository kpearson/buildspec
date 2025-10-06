"""Main Typer application instance."""

import typer
from cli.commands import create_epic, create_tickets, execute_epic, execute_ticket, init

app = typer.Typer(
    name="buildspec",
    help="Headless CLI for buildspec workflows - enables non-interactive execution via Claude Code CLI",
    add_completion=False
)

# Register commands
app.command(name="init")(init.command)
app.command(name="create-epic")(create_epic.command)
app.command(name="create-tickets")(create_tickets.command)
app.command(name="execute-epic")(execute_epic.command)
app.command(name="execute-ticket")(execute_ticket.command)


def main():
    """Entry point for pip-installed command."""
    app()


if __name__ == "__main__":
    main()
