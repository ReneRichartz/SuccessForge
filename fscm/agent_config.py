"""
Agent configurations for the multi-agent orchestration system.
Defines agent types, their LLM providers, tools, and system prompts.

Configuration is loaded from:
- config/agents.yaml: LLM provider, model, tools, temperature
- roles/<agent>.md: System prompts
"""

from dataclasses import dataclass
from typing import List, Dict
from pathlib import Path
import yaml


# Project root directory (parent of fscm/)
PROJECT_ROOT = Path(__file__).parent.parent
ROLES_DIR = PROJECT_ROOT / "roles"
CONFIG_DIR = PROJECT_ROOT / "config"
AGENTS_CONFIG_FILE = CONFIG_DIR / "agents.yaml"


@dataclass
class AgentConfig:
    """Configuration for a specialized agent."""
    name: str
    role: str
    system_prompt: str
    llm_provider: str  # "claude", "ollama", "openai"
    model: str
    tools: List[str]
    temperature: float = 0.7


def load_role_prompt(role_name: str, role_file: str = None) -> str:
    """
    Load system prompt from a markdown file in the roles/ directory.

    Args:
        role_name: The role name (e.g., "research", "architekt")
        role_file: Optional explicit path to role file relative to roles/
                   (e.g., "de/research.md", "en/architect.md")

    Returns:
        The content of the markdown file as system prompt

    Raises:
        FileNotFoundError: If the role file doesn't exist
    """
    # Use explicit role_file if provided, otherwise default to <role_name>.md
    if role_file:
        file_path = ROLES_DIR / role_file
    else:
        file_path = ROLES_DIR / f"{role_name}.md"

    if not file_path.exists():
        raise FileNotFoundError(f"Role file not found: {file_path}")

    return file_path.read_text(encoding="utf-8")


def load_agents_config() -> Dict:
    """
    Load agent configurations from YAML file.

    Returns:
        Dictionary with agent configurations

    Raises:
        FileNotFoundError: If config file doesn't exist
    """
    if not AGENTS_CONFIG_FILE.exists():
        raise FileNotFoundError(f"Config file not found: {AGENTS_CONFIG_FILE}")

    with open(AGENTS_CONFIG_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config.get("agents", {})


def _load_agent_configs() -> Dict[str, AgentConfig]:
    """
    Load all agent configurations from YAML and role files.

    Returns:
        Dictionary mapping agent names to their configurations
    """
    configs = {}

    try:
        agent_definitions = load_agents_config()
    except FileNotFoundError as e:
        print(f"Warning: {e}. Using default configurations.")
        agent_definitions = {}

    for agent_name, definition in agent_definitions.items():
        # Load system prompt from role file (use explicit role_file if configured)
        role_file = definition.get("role_file")
        try:
            system_prompt = load_role_prompt(agent_name, role_file)
        except FileNotFoundError as e:
            print(f"Warning: {e}. Using default system prompt.")
            system_prompt = f"Du bist ein {definition.get('name', agent_name)}."

        # Get tools list (handle both list and string "all")
        tools = definition.get("tools", [])
        if isinstance(tools, str):
            tools = [tools]

        configs[agent_name] = AgentConfig(
            name=definition.get("name", agent_name),
            role=definition.get("role", agent_name),
            system_prompt=system_prompt,
            llm_provider=definition.get("llm_provider", "ollama"),
            model=definition.get("model", "llama3"),
            tools=tools,
            temperature=definition.get("temperature", 0.7),
        )

    return configs


# Load configurations at module import
AGENT_CONFIGS: Dict[str, AgentConfig] = _load_agent_configs()


def get_agent_config(agent_name: str) -> AgentConfig:
    """Get configuration for a specific agent."""
    if agent_name not in AGENT_CONFIGS:
        available = ", ".join(AGENT_CONFIGS.keys())
        raise ValueError(f"Unknown agent: {agent_name}. Available agents: {available}")
    return AGENT_CONFIGS[agent_name]


def reload_agent_configs() -> None:
    """
    Reload all agent configurations from config and role files.
    Useful when configuration files have been modified.
    """
    global AGENT_CONFIGS
    AGENT_CONFIGS = _load_agent_configs()


def list_available_agents() -> List[str]:
    """List all available agent names."""
    return list(AGENT_CONFIGS.keys())


def get_roles_directory() -> Path:
    """Get the path to the roles directory."""
    return ROLES_DIR


def get_config_directory() -> Path:
    """Get the path to the config directory."""
    return CONFIG_DIR
