import logging
import os
from pathlib import Path
import dotenv

# Load .env BEFORE importing fscm modules
dotenv.load_dotenv(Path(__file__).parent / ".env", override=True)

import typer
from rich.console import Console
from rich.logging import RichHandler

from fscm import rag, agents

app = typer.Typer(
    name="fscm",
    help="CLI Framework for D365 FSCM Setup Automation",
    no_args_is_help=True,
)
console = Console()

app.add_typer(rag.app,name="RAG", help="Setup and manage RAG components")
app.add_typer(agents.app,name="Agents", help="Setup and manage Agents components")


@app.command()
def version():
    """Show version information."""
    from fscm import __version__
    console.print(f"FSCM Installer v{__version__}")


@app.command()
def init():
    console.print("[bold blue]Initializing FSCM...[/bold blue]")

if __name__ == "__main__":
    app()
