"""
Markdown Q&A Processor.
Reads a markdown file with questions, processes them through agents,
and writes answers back to the file.
"""

import re
from dataclasses import dataclass
from typing import List, Tuple, Optional
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .orchestrator import run_single_agent

console = Console()

# Regex pattern for numbered questions with optional @agent mention
# Matches: "1. @agent Question text" or "1. Question text"
QUESTION_PATTERN = re.compile(r'^(\d+)\.\s+(?:@(\w+)\s+)?(.+)$', re.MULTILINE)

# Pattern to detect a "Fragen" section header
QUESTIONS_SECTION_PATTERN = re.compile(r'^#{1,3}\s*Fragen\s*$', re.MULTILINE | re.IGNORECASE)

# Agent alias mapping (reuse from agents.py concept)
AGENT_ALIASES = {
    "research": ["research", "res", "r"],
    "projektleiter": ["projektleiter", "pm", "pl", "project"],
    "architekt": ["architekt", "architect", "arch", "sa"],
}


@dataclass
class Question:
    """Represents a parsed question from the markdown."""
    number: int          # Question number (1, 2, 3...)
    agent: str           # Agent to use ("research", "architekt", "pm")
    text: str            # The question text without @mention
    line_index: int      # Line position in original content
    original_line: str   # The original line for replacement


@dataclass
class Answer:
    """Represents an answer for a question."""
    question_number: int
    question_line: str   # Original question line
    question_text: str   # Clean question text (without @agent)
    answer_text: str     # The generated answer


def resolve_agent_alias(mention: Optional[str]) -> str:
    """
    Resolve an agent alias to the canonical agent name.

    Args:
        mention: The @mention text (without @), or None

    Returns:
        Canonical agent name (defaults to "research")
    """
    if not mention:
        return "research"

    mention_lower = mention.lower()

    for agent_name, aliases in AGENT_ALIASES.items():
        if mention_lower in aliases:
            return agent_name

    # Unknown alias, default to research
    console.print(f"[yellow]Warning: Unknown agent '@{mention}', using 'research'[/yellow]")
    return "research"


def parse_markdown_questions(content: str) -> Tuple[str, List[Question]]:
    """
    Parse a markdown file to extract context and questions.

    If a "## Fragen" section exists, only numbered items after it are treated as questions.
    Otherwise, questions are identified by:
    - Having an @agent mention, OR
    - Ending with a question mark (?)

    Context is everything before the questions section or first question.

    Args:
        content: The markdown file content

    Returns:
        Tuple of (context_text, list of Questions)
    """
    lines = content.split('\n')
    questions: List[Question] = []

    # Check for explicit "Fragen" section header
    questions_section_start = None
    for i, line in enumerate(lines):
        if QUESTIONS_SECTION_PATTERN.match(line.strip()):
            questions_section_start = i
            break

    # Determine where to start looking for questions
    search_start = questions_section_start + 1 if questions_section_start is not None else 0
    context_end_index = questions_section_start if questions_section_start is not None else len(lines)

    # Find all questions
    for i in range(search_start, len(lines)):
        line = lines[i]
        match = QUESTION_PATTERN.match(line.strip())
        if match:
            number = int(match.group(1))
            agent_mention = match.group(2)
            question_text = match.group(3).strip()

            # If no "Fragen" section, only treat as question if it has @mention or ends with ?
            if questions_section_start is None:
                if not agent_mention and not question_text.endswith('?'):
                    continue
                # First valid question marks end of context
                if not questions:
                    context_end_index = i

            agent = resolve_agent_alias(agent_mention)

            questions.append(Question(
                number=number,
                agent=agent,
                text=question_text,
                line_index=i,
                original_line=line
            ))

    # Extract context (everything before questions section or first question)
    context_lines = lines[:context_end_index]
    context = '\n'.join(context_lines).strip()

    return context, questions


def format_previous_answers(answers: List[Answer]) -> str:
    """
    Format all previous answers as context for subsequent questions.

    Args:
        answers: List of already answered questions

    Returns:
        Formatted string with previous Q&A pairs
    """
    if not answers:
        return ""

    parts = ["Bisherige Fragen und Antworten:\n"]
    for a in answers:
        parts.append(f"### {a.question_text}\n{a.answer_text}\n")

    return "\n".join(parts)


def process_questions(
    context: str,
    questions: List[Question],
    verbose: bool = True,
    debug: bool = False,
    project_id: Optional[int] = None,
    output_path: Optional[Path] = None,
    original_content: Optional[str] = None
) -> List[Answer]:
    """
    Process each question through its assigned agent.
    Writes to output file after EACH question if output_path is provided.
    Previous answers are included as context for subsequent questions.

    Args:
        context: The context text to prepend to each question
        questions: List of parsed questions
        verbose: Whether to show progress
        debug: Whether to enable debug mode for agents
        project_id: Optional project ID to filter RAG queries
        output_path: Optional path to write incremental results
        original_content: Original file content for incremental writes

    Returns:
        List of Answers
    """
    answers: List[Answer] = []

    if verbose:
        console.print(f"\n[bold cyan]Processing {len(questions)} questions...[/bold cyan]\n")

    for q in questions:
        if verbose:
            console.print(f"[bold]Question {q.number}:[/bold] {q.text}")
            console.print(f"[dim]Agent: {q.agent}[/dim]")

        # Build context with previous answers
        previous_answers_context = format_previous_answers(answers)

        # Build the full query with context and previous answers
        if previous_answers_context:
            full_query = f"""Kontext:
{context}

{previous_answers_context}

Aktuelle Frage:
{q.text}

Bitte beantworte die Frage basierend auf dem Kontext und den bisherigen Antworten."""
        else:
            full_query = f"""Kontext:
{context}

Frage:
{q.text}

Bitte beantworte die Frage basierend auf dem gegebenen Kontext."""

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            if verbose:
                progress.add_task(description=f"Agent '{q.agent}' arbeitet...", total=None)

            try:
                response = run_single_agent(q.agent, full_query, project_id=project_id, debug=debug)
            except Exception as e:
                response = f"Fehler bei der Verarbeitung: {str(e)}"
                console.print(f"[red]Error processing question {q.number}: {e}[/red]")

        answers.append(Answer(
            question_number=q.number,
            question_line=q.original_line,
            question_text=q.text,
            answer_text=response
        ))

        # Write incrementally after each question
        if output_path and original_content:
            result = write_answers_to_markdown(original_content, answers)
            output_path.write_text(result, encoding='utf-8')
            if verbose:
                console.print(f"[dim]Saved to {output_path}[/dim]")

        if verbose:
            # Show truncated preview
            preview = response[:200] + "..." if len(response) > 200 else response
            console.print(f"[green]Answer preview:[/green] {preview}\n")
            console.print("-" * 50)

    return answers


def write_answers_to_markdown(original_content: str, answers: List[Answer]) -> str:
    """
    Insert answers under their corresponding questions in the markdown.
    Questions are formatted as headers (### Question text) without @agent mentions.

    Args:
        original_content: The original markdown content
        answers: List of answers to insert

    Returns:
        Updated markdown content with answers
    """
    lines = original_content.split('\n')

    # Create a mapping of question line content to answer
    answer_map = {a.question_line.strip(): a for a in answers}

    result_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if this line is a question
        stripped = line.strip()
        if stripped in answer_map:
            answer = answer_map[stripped]

            # Replace the original question line with a formatted header (without @agent)
            result_lines.append(f"### {answer.question_text}")

            # Skip any existing answer block (lines starting with spaces until next numbered item or end)
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                # Stop if we hit another numbered question or non-indented content
                if next_line.strip() and QUESTION_PATTERN.match(next_line.strip()):
                    break
                # Stop if we hit a line that looks like a previous answer we should remove
                if next_line.strip().startswith("**Antwort:**") or next_line.strip().startswith("###"):
                    # Skip this old answer and its content
                    j += 1
                    while j < len(lines) and (not lines[j].strip() or lines[j].startswith("   ")):
                        if lines[j].strip() and QUESTION_PATTERN.match(lines[j].strip()):
                            break
                        j += 1
                    continue
                # Keep empty lines between question and next question
                if not next_line.strip():
                    j += 1
                    continue
                break

            # Insert the answer
            result_lines.append("")  # Empty line before answer
            result_lines.append(answer.answer_text)
            result_lines.append("")  # Empty line after answer

            # Move index past any skipped content
            i = j - 1
        else:
            result_lines.append(line)

        i += 1

    return '\n'.join(result_lines)


def process_markdown_file(
    file_path: str,
    output_path: Optional[str] = None,
    dry_run: bool = False,
    verbose: bool = True,
    debug: bool = False,
    project_id: Optional[int] = None
) -> str:
    """
    Main function to process a markdown file with questions.

    Args:
        file_path: Path to the input markdown file
        output_path: Optional output path (defaults to overwriting input)
        dry_run: If True, only display results without writing
        verbose: Whether to show progress
        debug: Whether to enable debug mode for agents
        project_id: Optional project ID to filter RAG queries

    Returns:
        The processed markdown content
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not path.suffix.lower() == '.md':
        console.print(f"[yellow]Warning: File does not have .md extension[/yellow]")

    # Read the file
    content = path.read_text(encoding='utf-8')

    if verbose:
        console.print(f"[bold green]Processing:[/bold green] {file_path}")
    if project_id:
        console.print(f"[bold magenta]Project Filter:[/bold magenta] {project_id}")
    if debug:
        console.print(f"[bold yellow]Debug Mode:[/bold yellow] Enabled")

    # Parse questions
    context, questions = parse_markdown_questions(content)

    if not questions:
        console.print("[yellow]No questions found in the file.[/yellow]")
        console.print("[dim]Questions should be numbered (1. 2. 3.) with optional @agent mentions[/dim]")
        return content

    if verbose:
        console.print(f"[bold]Found {len(questions)} questions[/bold]")
        console.print(f"[dim]Context length: {len(context)} characters[/dim]\n")

    # Determine output path for incremental writes
    out_path = Path(output_path) if output_path else path

    # Process questions - write incrementally after each answer (unless dry_run)
    answers = process_questions(
        context,
        questions,
        verbose,
        debug=debug,
        project_id=project_id,
        output_path=out_path if not dry_run else None,
        original_content=content
    )

    # Generate final output
    result = write_answers_to_markdown(content, answers)

    if dry_run:
        console.print("\n[bold yellow]DRY RUN - Output not written to file:[/bold yellow]\n")
        console.print("-" * 50)
        console.print(result)
        console.print("-" * 50)
    else:
        console.print(f"\n[bold green]Complete! Written to:[/bold green] {out_path}")

    return result
