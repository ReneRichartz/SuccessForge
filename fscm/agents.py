"""
Agent CLI commands and workflow management.
Refactored to use the modular multi-agent orchestration system.
"""

from dotenv import load_dotenv
from typing import TypedDict, Annotated, List, Optional, Tuple
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage
import operator
import re
from pathlib import Path

import typer
from rich.console import Console

# Load .env from project root before other imports
_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / ".env", override=True)

from .tools import get_all_tools
from .llm_factory import create_llm
from .agent_config import get_agent_config, list_available_agents
from .orchestrator import run_single_agent, run_orchestrated, AgentRunner
from .markdown_processor import process_markdown_file

# Agent mention aliases for convenience
AGENT_ALIASES = {
    "research": ["research", "res", "r"],
    "projektleiter": ["projektleiter", "pm", "pl", "project"],
    "architekt": ["architekt", "architect", "arch", "sa"],
}


def parse_agent_mention(query: str) -> Tuple[Optional[str], str]:
    """
    Parse @agent mentions from the query.

    Supports:
        @research, @res, @r
        @projektleiter, @pm, @pl, @project
        @architekt, @architect, @arch, @sa

    Args:
        query: The user query potentially containing @agent mention

    Returns:
        Tuple of (agent_name or None, cleaned query)
    """
    # Pattern to match @agent_name at the beginning or anywhere in the query
    pattern = r'@(\w+)'
    match = re.search(pattern, query)

    if not match:
        return None, query

    mention = match.group(1).lower()

    # Find the agent by alias
    for agent_name, aliases in AGENT_ALIASES.items():
        if mention in aliases:
            # Remove the @mention from the query
            cleaned_query = re.sub(r'@' + mention + r'\s*', '', query, flags=re.IGNORECASE).strip()
            return agent_name, cleaned_query

    # Unknown agent mention - return None and keep query as-is
    return None, query

app = typer.Typer(no_args_is_help=True)
console = Console()


class AgentState(TypedDict):
    """State for agent workflows."""
    messages: Annotated[List, operator.add]


def create_agent_workflow(agent_name: str = "research"):
    """
    Create an agent workflow for the specified agent.

    Args:
        agent_name: The agent configuration to use

    Returns:
        Compiled workflow
    """
    config = get_agent_config(agent_name)
    llm = create_llm(config.llm_provider, config.model, config.temperature)

    # Get tools for this agent
    from .tools import get_tools_for_agent
    tools = get_tools_for_agent(agent_name)

    llm_with_tools = llm.bind_tools(tools) if tools else llm
    tool_node = ToolNode(tools) if tools else None

    def call_model(state: AgentState):
        messages = state["messages"]
        # Prepend system message
        from langchain_core.messages import SystemMessage
        full_messages = [SystemMessage(content=config.system_prompt)] + messages
        response = llm_with_tools.invoke(full_messages)
        return {"messages": [response]}

    def should_continue(state: AgentState) -> str:
        last_message = state["messages"][-1]
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools"
        return "end"

    # Build workflow
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)

    if tool_node:
        workflow.add_node("tools", tool_node)
        workflow.add_conditional_edges(
            "agent",
            should_continue,
            {"tools": "tools", "end": END}
        )
        workflow.add_edge("tools", "agent")
    else:
        workflow.add_edge("agent", END)

    workflow.set_entry_point("agent")
    return workflow.compile()


# Default workflow (for backwards compatibility)
def get_default_workflow():
    """Get the default research agent workflow."""
    return create_agent_workflow("research")


def run_agent(query: str, agent_name: str = "research") -> str:
    """
    Run an agent with a given query.

    Args:
        query: The query/task for the agent
        agent_name: Which agent to use (default: research)

    Returns:
        The agent's response
    """
    wf = create_agent_workflow(agent_name)
    initial_state = {
        "messages": [HumanMessage(content=query)]
    }
    result = wf.invoke(initial_state)
    return result["messages"][-1].content


@app.command()
def test_agent():
    """Test the RAG agent with sample queries."""
    queries = [
        "What projects are available in the knowledge base?",
        "Search the knowledge base for information about requirements",
        "What's the weather like in New York?",
    ]

    for query in queries:
        console.print(f"\n[bold green]Query:[/bold green] {query}")
        console.print("-" * 50)
        response = run_agent(query)
        console.print(f"[bold blue]Response:[/bold blue] {response}\n")


@app.command()
def ask(
    query: str = typer.Argument(..., help="Question to ask the agent. Use @agent to specify agent (e.g., @research, @architekt, @pm)"),
    project_id: Optional[int] = typer.Option(None, "--project", "-p", help="Filter to specific project"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Specific agent to use (research, projektleiter, architekt)"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode to show system prompt and messages"),
):
    """
    Ask an agent a question about your D365 projects.

    You can specify the agent using @mentions in your query:
        @research, @res, @r       - Research Agent (Ollama)
        @projektleiter, @pm, @pl  - Projektleiter (Claude Sonnet)
        @architekt, @arch, @sa    - Solution Architekt (Claude Opus)

    Examples:
        ask "@research Was ist D365 Finance?"
        ask "@arch Erstelle eine Architektur für die Integration"
        ask "@pm Erstelle einen Projektplan"
        ask "@research Was ist D365?" --debug  # Mit Debug-Ausgabe
    """
    # Parse @agent mention from query (takes precedence over --agent flag)
    mentioned_agent, cleaned_query = parse_agent_mention(query)

    # Determine which agent to use: @mention > --agent flag > default
    if mentioned_agent:
        agent_name = mentioned_agent
        full_query = cleaned_query
    elif agent:
        agent_name = agent
        full_query = query
    else:
        agent_name = "research"
        full_query = query

    # Validate agent name
    available = list_available_agents()
    if agent_name not in available and agent_name != "supervisor":
        console.print(f"[bold red]Error:[/bold red] Unknown agent '{agent_name}'")
        console.print(f"Available agents: {', '.join([a for a in available if a != 'supervisor'])}")
        console.print("\n[bold]Agent aliases:[/bold]")
        for name, aliases in AGENT_ALIASES.items():
            console.print(f"  @{name}: {', '.join(['@' + a for a in aliases])}")
        raise typer.Exit(code=1)

    console.print(f"[bold green]Query:[/bold green] {full_query}")
    console.print(f"[bold cyan]Agent:[/bold cyan] {agent_name}")
    if project_id:
        console.print(f"[bold magenta]Project Filter:[/bold magenta] {project_id}")
    if debug:
        console.print(f"[bold yellow]Debug Mode:[/bold yellow] Enabled")
    console.print("-" * 50)

    # Pass project_id and debug to run_single_agent
    response = run_single_agent(agent_name, full_query, project_id=project_id, debug=debug)
    console.print(f"[bold blue]Response:[/bold blue] {response}")


@app.command()
def orchestrate(
    query: str = typer.Argument(..., help="Task to orchestrate across agents"),
):
    """
    Run a multi-agent orchestration with supervisor delegation.
    The supervisor will analyze the task and delegate to appropriate specialists.
    """
    console.print(f"[bold green]Task:[/bold green] {query}")
    console.print(f"[bold cyan]Mode:[/bold cyan] Multi-Agent Orchestration")
    console.print("-" * 50)

    response = run_orchestrated(query)
    console.print(f"[bold blue]Response:[/bold blue] {response}")


@app.command()
def list_agents():
    """List all available agents and their configurations."""
    from .agent_config import AGENT_CONFIGS

    console.print("\n[bold]Available Agents:[/bold]\n")

    for name, config in AGENT_CONFIGS.items():
        if name == "supervisor":
            continue  # Skip supervisor in listing

        # Get aliases for this agent
        aliases = AGENT_ALIASES.get(name, [name])
        alias_str = ", ".join([f"@{a}" for a in aliases])

        console.print(f"[bold cyan]{name}[/bold cyan]")
        console.print(f"  Name: {config.name}")
        console.print(f"  Role: {config.role}")
        console.print(f"  LLM: {config.llm_provider} / {config.model}")
        console.print(f"  Tools: {', '.join(config.tools)}")
        console.print(f"  Mentions: {alias_str}")
        console.print()


@app.command("process-file")
def process_file(
    file_path: str = typer.Argument(..., help="Path to the markdown file with questions"),
    project_id: Optional[int] = typer.Option(None, "--project", "-p", help="Filter RAG queries to specific project"),
    dry_run: bool = typer.Option(False, "--dry-run", "--dry", help="Show answers without writing to file"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path (default: overwrite original)"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode to show system prompt and messages"),
):
    """
    Process a markdown file with questions and insert answers.

    The markdown file should contain:
    - Context: Text before the first numbered question
    - Questions: Numbered list (1. 2. 3. ...) with optional @agent mentions

    Example input:
        # Project Title

        This is the context for all questions.

        1. @research What is D365 Finance?

        2. @architekt How should the integration be structured?

        3. Question without agent mention (uses research by default)

    Supported @mentions:
        @research, @res, @r       - Research Agent
        @projektleiter, @pm, @pl  - Projektleiter
        @architekt, @arch, @sa    - Solution Architekt
    """
    path = Path(file_path)

    if not path.exists():
        console.print(f"[bold red]Error:[/bold red] File not found: {file_path}")
        raise typer.Exit(code=1)

    try:
        process_markdown_file(
            file_path=str(path),
            output_path=output,
            dry_run=dry_run,
            verbose=True,
            debug=debug,
            project_id=project_id
        )
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


def format_chat_history(history: List[Tuple[str, str, str]]) -> str:
    """
    Format chat history as context for the next query.

    Args:
        history: List of (question, agent_name, answer) tuples

    Returns:
        Formatted string with chat history
    """
    if not history:
        return ""

    parts = ["Bisheriger Chat-Verlauf:\n"]
    for question, agent, answer in history:
        parts.append(f"User: {question}")
        parts.append(f"{agent.capitalize()}: {answer}\n")
    return "\n".join(parts)


def show_chat_help():
    """Show help for chat mode."""
    console.print("\n[bold]Chat-Befehle:[/bold]")
    console.print("  [cyan]exit[/cyan]   - Chat beenden")
    console.print("  [cyan]clear[/cyan]  - Chat-Verlauf löschen")
    console.print("  [cyan]help[/cyan]   - Diese Hilfe anzeigen")
    console.print()
    console.print("[bold]Agenten:[/bold]")
    for name, aliases in AGENT_ALIASES.items():
        alias_str = ", ".join([f"@{a}" for a in aliases])
        console.print(f"  [cyan]{alias_str}[/cyan] - {name.capitalize()}")
    console.print()
    console.print("[bold]Beispiele:[/bold]")
    console.print("  @research Was ist D365 Finance?")
    console.print("  @architekt Erstelle eine Architektur")
    console.print("  Erkläre das genauer (nutzt Standard-Agent)")
    console.print()


@app.command("chat")
def chat_mode(
    project_id: Optional[int] = typer.Option(None, "--project", "-p", help="Filter RAG queries to specific project"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode"),
):
    """
    Interaktiver Chat-Modus mit Projekt-Kontext.

    Startet einen interaktiven Chat-Loop, der bis zur Eingabe von "exit" läuft.
    Agenten werden über @mentions angesprochen (z.B. @research, @architekt, @pm).
    Der Chat-Verlauf wird automatisch als Kontext an nachfolgende Fragen übergeben.

    Beispiel:
        python main.py Agents chat -p 99
    """
    from rich.markdown import Markdown

    chat_history: List[Tuple[str, str, str]] = []  # (question, agent, answer)

    # Header
    console.print("\n[bold green]🚀 FSCM Chat Mode[/bold green]")
    if project_id:
        console.print(f"[bold magenta]📁 Projekt:[/bold magenta] {project_id}")
    console.print("[dim]💡 Agenten: @research, @architekt, @pm (Standard: research)[/dim]")
    console.print("[dim]💡 Befehle: exit, clear, help[/dim]")
    console.print()

    while True:
        try:
            user_input = console.input("[bold green]You:[/bold green] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]👋 Chat beendet (Ctrl+C)[/yellow]")
            break

        # Exit-Bedingung
        if user_input.lower() == "exit":
            console.print("[yellow]👋 Chat beendet.[/yellow]")
            break

        # Clear-Befehl
        if user_input.lower() == "clear":
            chat_history.clear()
            console.print("[cyan]🗑️ Chat-Verlauf gelöscht.[/cyan]")
            continue

        # Help-Befehl
        if user_input.lower() == "help":
            show_chat_help()
            continue

        # Leere Eingabe ignorieren
        if not user_input:
            continue

        # Agent parsen
        agent_name, cleaned_query = parse_agent_mention(user_input)
        if not agent_name:
            agent_name = "research"

        # Kontext aus Chat-History aufbauen
        context = format_chat_history(chat_history)

        # Query mit Kontext
        if context:
            full_query = f"{context}\n\nAktuelle Frage:\n{cleaned_query}"
        else:
            full_query = cleaned_query

        # Agent ausführen
        try:
            console.print(f"[dim]⏳ {agent_name.capitalize()} denkt nach...[/dim]")
            runner = AgentRunner(agent_name, project_id, debug)
            response = runner.run(full_query)

            # In History speichern
            chat_history.append((cleaned_query, agent_name, response))

            # Ausgabe
            console.print(f"\n[bold blue]🔧 {agent_name.capitalize()}:[/bold blue]")
            console.print(Markdown(response))
            console.print()

        except Exception as e:
            console.print(f"[bold red]❌ Fehler:[/bold red] {e}")
            if debug:
                import traceback
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
