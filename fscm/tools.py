"""
Tool definitions for the multi-agent system.
Extracts tools from the original agents.py for reuse across different agents.
"""

from typing import List, Optional
from langchain.tools import tool
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_tavily import TavilySearch
from dotenv import load_dotenv
from pathlib import Path
import os

# Load .env from project root
_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / ".env", override=True)

# Initialize shared components
embedding_function = OllamaEmbeddings(model="embeddinggemma")

# Project-specific document database
db = Chroma(
    embedding_function=embedding_function,
    persist_directory="./rag",
    collection_name="rag_collection"
)

# Global knowledge base (D365 docs, best practices, etc.)
knowledge_db = Chroma(
    embedding_function=embedding_function,
    persist_directory="./rag",
    collection_name="knowledge_base"
)

# Initialize Tavily search
tavily_search = TavilySearch(
    max_results=5,
    topic="general",
    include_answer=True,
)


@tool
def query_knowledge_base(query: str, project_id: Optional[int] = None, k: int = 5) -> str:
    """
    Search the knowledge base for relevant information about D365 FSCM projects.
    Automatically searches BOTH project-specific documents AND the global knowledge base.

    Args:
        query: The search query to find relevant documents
        project_id: Optional project ID to filter project results
        k: Number of results to return from each source (default 5)

    Returns:
        Combined results from project documents and global knowledge base
    """
    formatted_results = []
    result_num = 1

    # 1. Search project-specific documents
    try:
        if project_id:
            project_results = db.similarity_search(query, k=k, filter={"project_id": project_id})
        else:
            project_results = db.similarity_search(query, k=k)

        for doc in project_results:
            source = doc.metadata.get('source_file', 'Unknown')
            proj = doc.metadata.get('project_id', 'N/A')
            content = doc.page_content[:500]
            formatted_results.append(
                f"[{result_num}] [Projekt {proj}] {source}\n{content}\n"
            )
            result_num += 1
    except Exception as e:
        formatted_results.append(f"[Projekt-Suche Fehler: {str(e)}]")

    # 2. Search global knowledge base (ALWAYS)
    try:
        # Check if knowledge_base has any documents
        kb_count = len(knowledge_db.get()['ids'])
        if kb_count > 0:
            global_results = knowledge_db.similarity_search(query, k=3)
            for doc in global_results:
                source = doc.metadata.get('source_file', 'Unknown')
                content = doc.page_content[:500]
                formatted_results.append(
                    f"[{result_num}] [Wissensdatenbank] {source}\n{content}\n"
                )
                result_num += 1
    except Exception:
        pass  # Knowledge base may not exist yet

    if not formatted_results:
        return f"No relevant documents found for query: '{query}'"

    return "\n---\n".join(formatted_results)


def create_project_scoped_knowledge_base_tool(project_id: int):
    """Create a query_knowledge_base tool pre-filtered to a specific project.
    Also includes global knowledge base results."""

    @tool
    def query_project_knowledge_base(query: str, k: int = 5) -> str:
        """
        Search the knowledge base for relevant information.
        Results include project-specific documents AND the global knowledge base.

        Args:
            query: The search query to find relevant documents
            k: Number of results to return (default 5)

        Returns:
            Combined results from project and global knowledge base
        """
        formatted_results = []
        result_num = 1

        # 1. Project-specific results
        try:
            project_results = db.similarity_search(query, k=k, filter={"project_id": project_id})
            for doc in project_results:
                source = doc.metadata.get('source_file', 'Unknown')
                content = doc.page_content[:500]
                formatted_results.append(
                    f"[{result_num}] [Projekt {project_id}] {source}\n{content}\n"
                )
                result_num += 1
        except Exception as e:
            formatted_results.append(f"[Projekt-Suche Fehler: {str(e)}]")

        # 2. Global knowledge base (ALWAYS)
        try:
            kb_count = len(knowledge_db.get()['ids'])
            if kb_count > 0:
                global_results = knowledge_db.similarity_search(query, k=3)
                for doc in global_results:
                    source = doc.metadata.get('source_file', 'Unknown')
                    content = doc.page_content[:500]
                    formatted_results.append(
                        f"[{result_num}] [Wissensdatenbank] {source}\n{content}\n"
                    )
                    result_num += 1
        except Exception:
            pass

        if not formatted_results:
            return f"No relevant documents found for query: '{query}' in project {project_id}"

        return "\n---\n".join(formatted_results)

    query_project_knowledge_base.__doc__ = f"""
    Search the knowledge base for project {project_id}.
    Results include project-specific documents AND the global knowledge base.

    Args:
        query: The search query to find relevant documents
        k: Number of results to return (default 5)

    Returns:
        Combined results from project and global knowledge base
    """

    return query_project_knowledge_base


@tool
def list_projects() -> str:
    """
    List all projects available in the knowledge base.

    Returns:
        A list of project IDs and their associated files
    """
    try:
        all_docs = db.get()

        if not all_docs['ids']:
            return "No documents in knowledge base"

        # Collect project info
        projects = {}
        for metadata in all_docs['metadatas']:
            project_id = metadata.get('project_id', 'Unknown')
            source_file = metadata.get('source_file', 'Unknown')

            if project_id not in projects:
                projects[project_id] = set()
            projects[project_id].add(source_file)

        # Format output
        output = ["Available projects in knowledge base:\n"]
        for project_id, files in sorted(projects.items(), key=lambda x: str(x[0])):
            output.append(f"\nProject {project_id}: {len(files)} file(s)")
            for f in sorted(files)[:5]:  # Show max 5 files per project
                output.append(f"  - {f}")
            if len(files) > 5:
                output.append(f"  ... and {len(files) - 5} more")

        return "\n".join(output)
    except Exception as e:
        return f"Error listing projects: {str(e)}"


@tool
def web_search(query: str) -> str:
    """
    Search the web for current information using Tavily.
    Use this for questions about current events, documentation, or topics not in the knowledge base.

    Args:
        query: The search query

    Returns:
        Search results from the web
    """
    try:
        response = tavily_search.invoke(query)
        if not response:
            return f"No web results found for: {query}"

        # Extract results from response dict
        results = response.get('results', []) if isinstance(response, dict) else response

        if not results:
            # Return the answer if available
            answer = response.get('answer', '') if isinstance(response, dict) else ''
            if answer:
                return f"Answer: {answer}"
            return f"No web results found for: {query}"

        # Format results
        formatted = []
        for i, result in enumerate(results, 1):
            title = result.get('title', 'No title')
            url = result.get('url', '')
            content = result.get('content', '')[:300]
            formatted.append(f"[{i}] {title}\n    URL: {url}\n    {content}")

        # Include answer if available
        answer = response.get('answer', '') if isinstance(response, dict) else ''
        if answer:
            formatted.insert(0, f"Summary: {answer}\n")

        return "\n\n".join(formatted)
    except Exception as e:
        return f"Error searching web: {str(e)}"


@tool
def get_weather(city: str) -> str:
    """Get current weather information for a given city."""
    # Mock implementation – replace with real API call in production
    weather_data = {
        "New York": "Sunny, 72°F",
        "London": "Cloudy, 15°C",
        "Tokyo": "Rainy, 22°C"
    }
    return weather_data.get(city, "Weather data not available")


@tool
def calculate_sum(numbers: List[float]) -> float:
    """Calculate the sum of a list of numbers."""
    return sum(numbers)


@tool
def save_markdown(filename: str, content: str, folder: str = "./outputs") -> str:
    """
    Save content to a markdown file.

    Use this tool to save research results, documentation, architecture designs,
    or any other content to a markdown file for later reference.

    Args:
        filename: Name of the file (with or without .md extension)
        content: The markdown content to save
        folder: Folder to save the file in (default: ./outputs)

    Returns:
        Success message with file path or error message
    """
    try:
        from datetime import datetime

        # Ensure folder exists
        folder_path = Path(folder)
        folder_path.mkdir(parents=True, exist_ok=True)

        # Add .md extension if not present
        if not filename.endswith('.md'):
            filename = f"{filename}.md"

        file_path = folder_path / filename

        # Add header with timestamp
        header = f"<!-- Generated: {datetime.now().isoformat()} -->\n\n"
        file_path.write_text(header + content, encoding='utf-8')

        return f"✅ Saved to {file_path.absolute()}"
    except Exception as e:
        return f"❌ Error saving file: {str(e)}"


# Tool registry - maps tool names to tool objects
# Note: tavily_search is used internally by web_search, not exposed directly
TOOL_REGISTRY = {
    "query_knowledge_base": query_knowledge_base,
    "list_projects": list_projects,
    "web_search": web_search,
    "get_weather": get_weather,
    "calculate_sum": calculate_sum,
    "save_markdown": save_markdown,
}


def get_all_tools() -> list:
    """Get all available tools."""
    return list(TOOL_REGISTRY.values())


def get_tools_by_names(tool_names: List[str]) -> list:
    """Get specific tools by their names."""
    tools = []
    for name in tool_names:
        if name in TOOL_REGISTRY:
            tools.append(TOOL_REGISTRY[name])
        else:
            print(f"Warning: Unknown tool '{name}'")
    return tools


def get_tools_for_agent(agent_name: str) -> list:
    """
    Get the tools configured for a specific agent.

    Args:
        agent_name: The agent name from agent_config

    Returns:
        List of tool objects for the agent
    """
    from .agent_config import get_agent_config

    config = get_agent_config(agent_name)

    if "all" in config.tools:
        return get_all_tools()

    # For supervisor, return empty list (delegation is handled separately)
    if agent_name == "supervisor":
        return []

    return get_tools_by_names(config.tools)
