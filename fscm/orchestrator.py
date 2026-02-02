"""
Multi-Agent Orchestrator with Supervisor pattern.
Coordinates specialized agents for D365 FSCM project tasks.
"""

from typing import TypedDict, Annotated, List, Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain.tools import tool
import operator
import time

# Retry configuration for rate limits
MAX_RETRIES = 3
INITIAL_WAIT_SECONDS = 60  # Rate limit is per minute

from .agent_config import get_agent_config, AGENT_CONFIGS, AgentConfig
from .llm_factory import create_llm_from_config
from .tools import get_tools_for_agent, get_all_tools


class OrchestratorState(TypedDict):
    """State for the orchestrator workflow."""
    messages: Annotated[List, add_messages]
    current_agent: str
    agent_results: Dict[str, str]
    final_response: Optional[str]


class AgentRunner:
    """Runs individual agents with their configured LLM and tools."""

    def __init__(self, agent_name: str, project_id: Optional[int] = None, debug: bool = False):
        self.agent_name = agent_name
        self.project_id = project_id
        self.debug = debug
        self.config = get_agent_config(agent_name)
        self.llm = create_llm_from_config(self.config)
        self.tools = self._get_tools_with_project_filter()
        self.llm_with_tools = self.llm.bind_tools(self.tools) if self.tools else self.llm

    def _debug_print(self, label: str, content: str, color: str = "yellow"):
        """Print debug information if debug mode is enabled."""
        if self.debug:
            from rich.console import Console
            from rich.panel import Panel
            console = Console()
            console.print(Panel(content, title=f"[bold {color}]{label}[/bold {color}]", border_style=color))

    def _get_tools_with_project_filter(self):
        """Get tools, replacing query_knowledge_base with project-scoped version if needed."""
        tools = get_tools_for_agent(self.agent_name)

        if self.project_id:
            # Replace generic tool with project-scoped version
            from .tools import create_project_scoped_knowledge_base_tool
            scoped_tool = create_project_scoped_knowledge_base_tool(self.project_id)

            tools = [
                scoped_tool if t.name == "query_knowledge_base" else t
                for t in tools
            ]

        return tools

    def _format_messages_for_debug(self, messages: List) -> str:
        """Format messages list for debug output."""
        lines = []
        for i, msg in enumerate(messages):
            msg_type = type(msg).__name__
            if hasattr(msg, 'content'):
                content = msg.content
                # Handle list content (Claude returns list of content blocks)
                if isinstance(content, list):
                    content = str(content)
                content = content[:200] + "..." if len(content) > 200 else content
            else:
                content = str(msg)[:200]

            # Show tool calls if present
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                tool_info = ", ".join([f"{tc.get('name', '?')}({tc.get('args', {})})" for tc in msg.tool_calls])
                lines.append(f"[{i}] {msg_type}: {content}\n    Tool calls: {tool_info}")
            else:
                lines.append(f"[{i}] {msg_type}: {content}")
        return "\n".join(lines)

    def _invoke_with_retry(self, messages: List, max_retries: int = MAX_RETRIES) -> Any:
        """
        Invoke LLM with automatic retry on rate limit errors (429).

        Args:
            messages: The messages to send to the LLM
            max_retries: Maximum number of retry attempts

        Returns:
            The LLM response

        Raises:
            Exception: If max retries exceeded or non-rate-limit error occurs
        """
        wait_time = INITIAL_WAIT_SECONDS

        for attempt in range(max_retries + 1):
            try:
                return self.llm_with_tools.invoke(messages)
            except Exception as e:
                error_str = str(e)

                # Check for rate limit error (429)
                if "429" in error_str or "rate_limit" in error_str.lower():
                    if attempt < max_retries:
                        self._debug_print(
                            "Rate Limit",
                            f"Rate limit erreicht. Warte {wait_time} Sekunden... (Versuch {attempt + 1}/{max_retries})",
                            "red"
                        )
                        # Show in console (even without debug mode)
                        from rich.console import Console
                        console = Console()
                        console.print(f"[yellow]⏳ Rate limit (429) - warte {wait_time}s vor Retry...[/yellow]")

                        time.sleep(wait_time)
                        wait_time = min(wait_time * 2, 300)  # Exponential backoff, max 5 min
                        continue
                    else:
                        raise Exception(f"Rate limit: Max retries ({max_retries}) überschritten. {error_str}")
                else:
                    # Other error, don't retry
                    raise

        raise Exception("Max retries exceeded")

    def run(self, query: str) -> str:
        """Run the agent with a query and return the response."""
        messages = [
            SystemMessage(content=self.config.system_prompt),
            HumanMessage(content=query)
        ]

        # Debug: Show initial setup
        self._debug_print("System Prompt", self.config.system_prompt, "cyan")
        self._debug_print("User Query", query, "green")
        self._debug_print("Available Tools", ", ".join([t.name for t in self.tools]) if self.tools else "None", "magenta")

        # Build tool lookup dict
        tools_by_name = {t.name: t for t in self.tools}

        # Simple agent loop with tool handling
        max_iterations = 10
        for iteration in range(max_iterations):
            self._debug_print(f"Iteration {iteration + 1}", "Invoking LLM...", "yellow")

            # Use retry logic for rate limit handling
            response = self._invoke_with_retry(messages)
            messages.append(response)

            # Debug: Show LLM response
            if hasattr(response, 'content') and response.content:
                # Handle both string and list content (Claude returns list of content blocks)
                content = response.content
                if isinstance(content, list):
                    content = str(content)
                content_preview = content[:500] + ("..." if len(content) > 500 else "")
                self._debug_print(f"LLM Response", content_preview, "blue")

            # Check for tool calls
            if hasattr(response, 'tool_calls') and response.tool_calls:
                # Execute each tool call directly
                for tool_call in response.tool_calls:
                    tool_name = tool_call.get('name', '')
                    tool_args = tool_call.get('args', {})
                    tool_id = tool_call.get('id', '')

                    self._debug_print(f"Tool Call: {tool_name}", f"Args: {tool_args}", "magenta")

                    if tool_name in tools_by_name:
                        try:
                            result = tools_by_name[tool_name].invoke(tool_args)
                        except Exception as e:
                            result = f"Error executing tool {tool_name}: {str(e)}"
                    else:
                        result = f"Unknown tool: {tool_name}"

                    self._debug_print(f"Tool Result: {tool_name}", str(result)[:500] + ("..." if len(str(result)) > 500 else ""), "green")

                    # Add tool result message
                    messages.append(ToolMessage(
                        content=str(result),
                        tool_call_id=tool_id
                    ))
            else:
                # No tool calls, return the response
                self._debug_print("Final Messages", self._format_messages_for_debug(messages), "cyan")
                return response.content

        self._debug_print("Final Messages", self._format_messages_for_debug(messages), "cyan")
        return response.content


class Orchestrator:
    """
    Supervisor-based orchestrator that coordinates multiple agents.
    Uses Claude Sonnet to analyze tasks and delegate to specialized agents.
    """

    def __init__(self):
        self.supervisor_config = get_agent_config("supervisor")
        self.supervisor_llm = create_llm_from_config(self.supervisor_config)
        self.agent_runners: Dict[str, AgentRunner] = {}

        # Initialize agent runners
        for agent_name in ["research", "projektleiter", "architekt"]:
            self.agent_runners[agent_name] = AgentRunner(agent_name)

        # Create delegation tool
        self._setup_delegation_tool()

    def _setup_delegation_tool(self):
        """Setup the delegation tool for the supervisor."""

        @tool
        def delegate_to_agent(agent_name: str, task: str) -> str:
            """
            Delegate a task to a specialized agent.

            Args:
                agent_name: The agent to delegate to ("research", "projektleiter", "architekt")
                task: The task description for the agent

            Returns:
                The agent's response
            """
            if agent_name not in self.agent_runners:
                available = ", ".join(self.agent_runners.keys())
                return f"Error: Unknown agent '{agent_name}'. Available agents: {available}"

            runner = self.agent_runners[agent_name]
            result = runner.run(task)
            return f"[{runner.config.name}]: {result}"

        self.delegation_tool = delegate_to_agent
        self.supervisor_with_tools = self.supervisor_llm.bind_tools([delegate_to_agent])

    def run(self, query: str) -> str:
        """
        Run the orchestrator with a query.
        The supervisor will analyze the query and delegate to appropriate agents.
        """
        messages = [
            SystemMessage(content=self.supervisor_config.system_prompt),
            HumanMessage(content=query)
        ]

        # Supervisor loop with delegation
        max_iterations = 10
        agent_responses = []

        for _ in range(max_iterations):
            response = self.supervisor_with_tools.invoke(messages)
            messages.append(response)

            # Check for tool calls (delegations)
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tool_call in response.tool_calls:
                    agent_name = tool_call["args"].get("agent_name", "")
                    task = tool_call["args"].get("task", "")

                    if agent_name in self.agent_runners:
                        runner = self.agent_runners[agent_name]
                        result = runner.run(task)
                        agent_responses.append((runner.config.name, result))

                        # Add tool result to messages
                        from langchain_core.messages import ToolMessage
                        tool_msg = ToolMessage(
                            content=f"[{runner.config.name}]: {result}",
                            tool_call_id=tool_call["id"]
                        )
                        messages.append(tool_msg)
                    else:
                        from langchain_core.messages import ToolMessage
                        tool_msg = ToolMessage(
                            content=f"Error: Unknown agent '{agent_name}'",
                            tool_call_id=tool_call["id"]
                        )
                        messages.append(tool_msg)
            else:
                # No more delegations, supervisor is done
                break

        # Return the final response
        return response.content


def run_single_agent(agent_name: str, query: str, project_id: Optional[int] = None, debug: bool = False) -> str:
    """
    Run a single agent directly without supervisor.

    Args:
        agent_name: The agent to run ("research", "projektleiter", "architekt")
        query: The query/task for the agent
        project_id: Optional project ID to filter knowledge base results
        debug: Enable debug mode to show system prompt and messages

    Returns:
        The agent's response
    """
    runner = AgentRunner(agent_name, project_id=project_id, debug=debug)
    return runner.run(query)


def run_orchestrated(query: str) -> str:
    """
    Run the full orchestration with supervisor.

    Args:
        query: The task to orchestrate

    Returns:
        The orchestrated response
    """
    orchestrator = Orchestrator()
    return orchestrator.run(query)
