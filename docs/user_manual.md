# User Manual: FSCM Multi-Agent System

## Overview

The FSCM Multi-Agent System allows you to automatically answer questions in Markdown files using AI agents. Answers are inserted directly into the file. The system supports multiple specialized agents, a global knowledge base, and automatic rate-limit handling.

## Quick Start

```bash
# Answer questions and update file
python main.py Agents process-file my_questions.md

# Preview without changes (Dry-Run)
python main.py Agents process-file my_questions.md --dry-run

# With project filter (RAG queries only from project 99)
python main.py Agents process-file my_questions.md -p 99

# With debug output (shows system prompts, messages, tool calls)
python main.py Agents process-file my_questions.md -d
```

---

## Setup Process

Before you can use the system, the following steps must be completed:

```
┌─────────────────────────────────────────────────────────────────┐
│  Setup Order                                                    │
├─────────────────────────────────────────────────────────────────┤
│  1. .env             → Configure API keys                       │
│  2. agents.yaml      → Configure agents & LLMs                  │
│  3. Knowledge RAG    → Import global D365 knowledge             │
│  4. Project RAG      → Import project-specific documents        │
│  5. Question Catalog → Create Markdown file with questions      │
└─────────────────────────────────────────────────────────────────┘
```

### Step 1: Environment Configuration (.env)

Create a `.env` file in the project directory:

```bash
cp .env.example .env
```

**Required API Keys:**

| Variable | Description | Required for |
|----------|-------------|--------------|
| `ANTHROPIC_API_KEY` | Anthropic Claude API | `llm_provider: claude` |
| `OPENAI_API_KEY` | OpenAI API | `llm_provider: openai` |
| `TAVILY_API_KEY` | Tavily Web Search | `web_search` tool |

**Example `.env`:**

```bash
# LLM Provider (at least one required)
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
OPENAI_API_KEY=sk-proj-xxxxx

# Ollama (for local LLMs)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3

# Web Search
TAVILY_API_KEY=tvly-xxxxx

# Agent Settings
AGENT_MAX_ITERATIONS=10
AGENT_VERBOSE=true
```

**Get API Keys:**
- Anthropic: https://console.anthropic.com/
- OpenAI: https://platform.openai.com/api-keys
- Tavily: https://tavily.com/

---

### Step 2: Agent Configuration (config/agents.yaml)

Configure the agents according to your needs:

```yaml
agents:
  research:
    name: "Research Agent"
    role: "researcher"
    role_file: "en/research.md"      # Minimal role (English)
    # role_file: "research.md"       # Detailed role
    # role_file: "de/research.md"    # Minimal role (German)
    llm_provider: "ollama"           # ollama, claude, openai
    model: "llama3"                  # Model name
    temperature: 0.3
    tools:
      - "web_search"
      - "query_knowledge_base"
      - "list_projects"
      - "save_markdown"
```

**Key Decisions:**

| Setting | Options | Recommendation |
|---------|---------|----------------|
| `llm_provider` | ollama, claude, openai | `ollama` for cost, `openai` for quality |
| `role_file` | de/*.md, en/*.md, *.md | `en/` for short prompts, root for detailed |
| `temperature` | 0.0 - 1.0 | 0.3 for precise, 0.7 for creative answers |

---

### Step 3: Global Knowledge Base (Knowledge RAG)

Import general D365 knowledge that should be available for **all** projects:

```bash
# Import folder with D365 documentation
python main.py RAG add-knowledge -f ./d365_documentation

# Import single file
python main.py RAG add-knowledge -f ./D365_Finance_Guide.pdf

# Check contents
python main.py RAG list-knowledge
```

**Suitable Documents:**
- Microsoft D365 documentation (PDFs)
- Best practices & lessons learned
- Architecture guides
- Technical references

**Output:**
```
📚 Adding to global knowledge base...
  ✅ D365_Finance_Guide.pdf (234 chunks)
  ✅ Integration_Best_Practices.md (56 chunks)
  ✅ Data_Migration_Handbook.pdf (189 chunks)
```

---

### Step 4: Project Knowledge Base (Project RAG)

Import project-specific documents with a `project_id`:

```bash
# Import project documents (Project ID: 99)
python main.py RAG addfiles -f ./project_99_docs -p 99

# Another project
python main.py RAG addfiles -f ./project_100_docs -p 100

# Show project documents
python main.py RAG delete --project 99 --dry-run
```

**Suitable Documents:**
- Requirements documents
- Specifications
- Project plans
- Architecture diagrams
- Meeting minutes

**Output:**
```
📁 Adding to project 99...
  ✅ Requirements.pdf (123 chunks)
  ✅ Specification_v2.docx (89 chunks)
  ✅ Architecture_Draft.md (45 chunks)
```

---

### Step 5: Create Question Catalog

Create a Markdown file with your questions:

```markdown
# Project: D365 Finance Implementation

## Context

### Company
- Industry: Manufacturing
- Employees: 500
- Locations: 3 (DACH region)

### Current Situation
- Current ERP: SAP R/3 (15 years old)
- Problems: Performance, no cloud connectivity
- Budget: 500,000 EUR
- Timeline: 12 months

### Goals
- Migration to D365 Finance & SCM
- Integration with existing CRM (Salesforce)
- Automation of warehouse management

---

## Questions

1. @research What are the main differences between SAP R/3 and D365 Finance?

2. @research Which D365 modules are relevant for a manufacturing company?

3. @architect Create a high-level architecture for the D365-Salesforce integration

4. @architect What data migration strategy do you recommend for the SAP migration?

5. @pm Create a project plan with milestones for the 12-month implementation

6. @pm What resources and roles are needed for the project?

7. @research What risks are there in a SAP-to-D365 migration?

8. @pm Create a risk matrix based on the identified risks
```

**Execute:**

```bash
# Dry-run (preview)
python main.py Agents process-file project_questions.md --dry-run -p 99

# Actually execute
python main.py Agents process-file project_questions.md -p 99

# With debug output
python main.py Agents process-file project_questions.md -p 99 -d
```

---

### Verify Setup

Check that everything is configured correctly:

```bash
# 1. List agents
python main.py Agents list-agents

# 2. Check knowledge base
python main.py RAG list-knowledge

# 3. Ask test question
python main.py Agents ask "@research What is D365 Finance?" -p 99

# 4. Test chat mode
python main.py Agents chat -p 99
```

**Expected Output (list-agents):**
```
Available Agents:

research
  Name: Research Agent
  Role: researcher
  LLM: ollama / llama3
  Tools: web_search, query_knowledge_base, list_projects, save_markdown
  Mentions: @research, @res, @r

architekt
  Name: Solution Architect
  Role: architect
  LLM: openai / gpt-4.1
  ...
```

---

## Markdown Format

### Basic Structure

An input file consists of two parts:

1. **Context** - Everything before the first numbered question
2. **Questions** - Numbered list with optional @agent mentions

### Example Input File

```markdown
# Project: D365 Finance Integration

## Background
The company wants to replace its existing ERP solution with
Microsoft Dynamics 365 Finance. Integration with the existing
CRM system is required.

## Budget
500,000 EUR

## Timeline
12 months

1. @research What are the main features of D365 Finance?

2. @architect How should the integration with CRM be structured?

3. @pm Create a rough project plan for the implementation

4. What risks are there in the migration?
```

### Format Rules

| Element | Rule |
|---------|------|
| **Context** | Any text before the first numbered question |
| **Questions** | Must be numbered: `1.`, `2.`, `3.` etc. |
| **@Mention** | Optional, determines the agent (default: research) |
| **Question text** | Any text after the number (and optional @mention) |

---

## Output Format

After processing, answers are inserted directly below the questions.
**Questions are formatted as headings and the @agent part is removed:**

### Before (Input)

```markdown
# Project

Project context...

1. @research What is D365?

2. @pm Create a timeline
```

### After (Output)

```markdown
# Project

Project context...

### What is D365?

Microsoft Dynamics 365 is a suite of
enterprise applications that combines ERP and CRM functionality...

### Create a timeline

Based on the project context, I recommend
the following timeline:
- Phase 1: Analysis (4 weeks)
- Phase 2: Design (6 weeks)
...
```

### Incremental Writing

The output file is written **after each answered question**, not at the end. This allows you to:
- Track progress live
- Keep already answered questions if interrupted
- Interrupt long processing at any time

### Context Chaining

Subsequent questions automatically receive **all** previous answers as context. This allows you to refer to previous answers:

```markdown
1. @research What is D365 Finance?

2. @research Explain that in more detail  # Refers to answer 1

3. @pm Based on the information, create a plan  # Refers to answers 1+2
```

---

## Available Agents

Agents can be customized via configuration files. See section [Agent Configuration](#agent-configuration) for details.

### @research (Default)

**Aliases:** `@research`, `@res`, `@r`

The Research Agent specializes in:
- Fact research
- Information gathering
- Knowledge base queries

**LLM:** Ollama (local)

**Example:**
```markdown
1. @research What is Microsoft Dynamics 365?
1. @res What modules are available in D365 Finance?
1. @r Explain the difference between D365 Finance and Business Central
```

### @architect

**Aliases:** `@architekt`, `@architect`, `@arch`, `@sa`

The Solution Architect specializes in:
- Technical architecture
- Integration design
- System landscapes
- Best practices

**LLM:** OpenAI GPT-4.1

**Example:**
```markdown
2. @architect Create an integration architecture for D365 and Salesforce
2. @arch What API strategy do you recommend?
2. @sa How should the data migration be structured?
```

### @projektleiter (Project Manager)

**Aliases:** `@projektleiter`, `@pm`, `@pl`, `@project`

The Project Manager specializes in:
- Project planning
- Resource management
- Risk assessment
- Milestones

**LLM:** OpenAI GPT-4.1

**Example:**
```markdown
3. @pm Create a project plan for the D365 implementation
3. @projektleiter What resources are needed?
3. @pl Identify the critical milestones
```

---

## Knowledge Base

The system uses two separate knowledge bases:

### Project Knowledge Base (rag_collection)

Project-specific documents with `project_id`:

```bash
# Import documents to project 99
python main.py RAG addfiles -f ./project_docs -p 99

# Show project documents
python main.py RAG delete --project 99 --dry-run
```

### Global Knowledge Base (knowledge_base)

General knowledge (D365 docs, best practices, etc.) **without** project_id:

```bash
# Import global knowledge
python main.py RAG add-knowledge -f ./d365_documentation

# Show contents
python main.py RAG list-knowledge

# Delete
python main.py RAG delete-knowledge --file "D365_Guide.pdf"
python main.py RAG delete-knowledge --all
```

### Automatic Combined Search

Every RAG query searches **BOTH** databases:

```
Query: "What is D365 Finance?"
    │
    ├──► Search in rag_collection (Project) → 3 results
    │
    ├──► Search in knowledge_base (Global) → 2 results
    │
    └──► Combined response: 5 results
```

**Example Output:**
```
[1] [Project 99] Requirements.pdf
The requirements for the system are...

---

[2] [Project 99] Timeline.xlsx
The timeline includes...

---

[3] [Knowledge Base] D365_Finance_Guide.pdf
D365 Finance is an ERP module for...
```

---

## CLI Commands

### Markdown Processing

```bash
python main.py Agents process-file <FILE> [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--project` | `-p` | Filter RAG queries to a specific project |
| `--debug` | `-d` | Show debug output (System Prompt, Messages, Tool Calls) |
| `--dry-run` | `--dry` | Show answers without modifying the file |
| `--output` | `-o` | Write to a different file instead of overwriting the original |

### RAG Commands

```bash
# Project documents
python main.py RAG addfiles -f <FOLDER> -p <PROJECT_ID>
python main.py RAG delete --project <PROJECT_ID>
python main.py RAG delete --file <FILENAME>

# Global knowledge base
python main.py RAG add-knowledge -f <FOLDER>
python main.py RAG list-knowledge
python main.py RAG delete-knowledge --file <FILENAME>
python main.py RAG delete-knowledge --all
```

### Agent Commands

```bash
# Ask a single question
python main.py Agents ask "@research What is D365?" -p 99
python main.py Agents ask "@architect Create an architecture" -d

# List agents
python main.py Agents list-agents

# Orchestration (Supervisor delegates)
python main.py Agents orchestrate "Analyze the project"

# Interactive chat mode
python main.py Agents chat -p 99
python main.py Agents chat -p 99 -d  # With debug output
```

---

## Interactive Chat Mode

The chat mode enables interactive conversation with the agents. The chat history is automatically passed as context to subsequent questions.

### Starting

```bash
python main.py Agents chat -p 99
```

### How It Works

```
🚀 FSCM Chat Mode
📁 Project: 99
💡 Agents: @research, @architect, @pm (Default: research)
💡 Commands: exit, clear, help

You: @research What is D365 Finance?

🔧 Research:
Microsoft Dynamics 365 Finance is an ERP module for...

You: Explain that in more detail

🔧 Research:
Based on my previous answer, I'd like to add...

You: @architect How would you implement that?

🔧 Architect:
Based on the information about D365 Finance, I recommend...

You: clear
🗑️ Chat history cleared.

You: exit
👋 Chat ended.
```

### Chat Commands

| Command | Description |
|---------|-------------|
| `exit` | End chat |
| `clear` | Clear chat history (context is reset) |
| `help` | Show help |
| `Ctrl+C` | End chat immediately |

### Context Chaining

The chat history is automatically appended as context to each new question. This allows you to:
- Refer to previous answers
- Ask follow-up questions without repetition
- Switch between agents (context is preserved)

---

## Rate Limit Handling

The system handles API rate limits (429 errors) automatically:

```
Question 1 → OK
Question 2 → OK
...
Question 26 → 429 Error
           → "⏳ Rate limit (429) - waiting 60s before retry..."
           → [60 second pause]
           → Retry → OK
Question 27 → OK
```

**Configuration:**
- Max. 3 retries
- Exponential backoff: 60s → 120s → 240s (max. 5 min)
- Message appears even without debug mode

**Context Passing:**
- All previous answers are passed as context to subsequent questions
- With many questions, this can lead to large token amounts

---

## Project Filter

With the `--project` / `-p` parameter, RAG queries can be restricted to a specific project.

### Usage

```bash
# Only search documents from project 99
python main.py Agents process-file questions.md -p 99
```

### How It Works

When a project filter is active:
1. Project documents are searched with the filter
2. The **global knowledge base is ALWAYS searched additionally**
3. Both results are combined

| Situation | Recommendation |
|-----------|----------------|
| Questions about a specific project | Use `-p <project_id>` |
| General questions about D365 | Don't use a filter |
| Comparison between projects | Don't use a filter |

---

## Debug Mode

Debug mode shows detailed information about agent execution.

### Usage

```bash
python main.py Agents process-file questions.md -d
```

### Debug Mode Output

| Information | Description |
|-------------|-------------|
| **System Prompt** | The complete system prompt of the agent |
| **User Query** | The query sent to the agent (context + question) |
| **Available Tools** | List of available tools |
| **Iteration X** | Each LLM call |
| **LLM Response** | The LLM's response |
| **Tool Call** | Which tool is called with which arguments |
| **Tool Result** | The result of the tool call |
| **Rate Limit** | Information about rate-limit retries |

---

## Agent Configuration

Agents are fully configurable via two types of files:

### Directory Structure

```
FSCMV3/
├── config/
│   └── agents.yaml         # LLM configuration (Provider, Model, Tools, Role-File)
├── roles/
│   ├── research.md         # System prompt (detailed)
│   ├── projektleiter.md    # System prompt (detailed)
│   ├── architekt.md        # System prompt (detailed)
│   ├── supervisor.md       # System prompt (detailed)
│   ├── de/                 # Minimal German roles
│   │   ├── research.md
│   │   ├── projektleiter.md
│   │   ├── architekt.md
│   │   └── supervisor.md
│   └── en/                 # Minimal English roles
│       ├── research.md
│       ├── project_manager.md
│       ├── architect.md
│       └── supervisor.md
```

### LLM Configuration (config/agents.yaml)

```yaml
agents:
  research:
    name: "Research Agent"
    role: "researcher"
    role_file: "de/research.md"      # Path relative to roles/
    llm_provider: "ollama"           # ollama, claude, openai
    model: "gpt-oss:120b-cloud"
    temperature: 0.3
    tools:
      - "web_search"
      - "query_knowledge_base"
      - "list_projects"
      - "save_markdown"

  projektleiter:
    name: "Project Manager"
    role: "project_manager"
    role_file: "de/projektleiter.md"
    llm_provider: "openai"
    model: "gpt-4.1"
    temperature: 0.3
    tools:
      - "all"

  architekt:
    name: "Solution Architect"
    role: "architect"
    role_file: "de/architekt.md"
    llm_provider: "openai"
    model: "gpt-4.1"
    temperature: 0.3
    tools:
      - "query_knowledge_base"
      - "list_projects"
      - "web_search"
      - "save_markdown"
```

### Role-File Configuration

The `role_file` field determines which Markdown file is used as the system prompt:

| Value | Path | Description |
|-------|------|-------------|
| `"research.md"` | `roles/research.md` | Detailed system prompt (~1700 lines) |
| `"de/research.md"` | `roles/de/research.md` | Minimal system prompt in German (~25 lines) |
| `"en/research.md"` | `roles/en/research.md` | Minimal system prompt in English (~25 lines) |

**If `role_file` is not specified**, it automatically uses `<agent_name>.md`.

**Example for English agents:**

```yaml
agents:
  research:
    role_file: "en/research.md"    # English minimal role
  architekt:
    role_file: "en/architect.md"   # English minimal role
  projektleiter:
    role_file: "en/project_manager.md"  # English minimal role
```

### Available LLM Providers

| Provider | Description | Example Models |
|----------|-------------|----------------|
| `ollama` | Local LLMs via Ollama | `llama3`, `mistral`, `gpt-oss:120b-cloud` |
| `claude` | Anthropic Claude API | `claude-sonnet-4-20250514` |
| `openai` | OpenAI API | `gpt-4`, `gpt-4-turbo`, `gpt-4.1` |

### Available Tools

| Tool | Description |
|------|-------------|
| `query_knowledge_base` | Searches project knowledge base + global knowledge base |
| `list_projects` | Lists all projects in the knowledge base |
| `web_search` | Web search via Tavily |
| `save_markdown` | Saves results as a Markdown file |
| `all` | Access to all available tools |

---

## save_markdown Tool

The `save_markdown` tool allows agents to save results as Markdown files.

### Usage

Ask the agent to save the result:

```
You: @research Research D365 Finance features and save the result

🔧 Research:
[Researches and calls save_markdown tool]
✅ Saved to /Users/.../outputs/d365_finance_features.md
```

Or with explicit filename:

```
You: @architect Create an architecture and save it as api_architecture.md
```

### Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `filename` | Filename (with or without .md) | - |
| `content` | The content to save | - |
| `folder` | Target folder | `./outputs` |

### Output Format

Saved files contain a timestamp header:

```markdown
<!-- Generated: 2025-02-02T14:30:00.000000 -->

# D365 Finance Features

...
```

### Assigned to

- `research` - Save research results
- `architect` - Save architecture documents
- `projektleiter` - Has `all` tools (automatically included)

### System Prompts (roles/*.md)

Each agent has its own Markdown file for its system prompt:

**Example: roles/research.md**

```markdown
# Research Agent

You are a research specialist for D365 Finance and Supply Chain Management.

## Main Tasks

- Research information about D365 FSCM features
- Search the knowledge base
- Web research for current documentation

## Instructions

Always respond in German and structure your results clearly.
```

---

## Tips & Best Practices

### Optimizing Context

The more relevant context, the better the answers:

```markdown
# Project: ERP Migration

## Company Profile
- Industry: Manufacturing
- Employees: 500
- Locations: 3 (Germany, Austria, Switzerland)

## Current Situation
- Legacy ERP: SAP R/3
- Age: 15 years
- Main problems: Performance, missing cloud connectivity

1. @research Which D365 modules are relevant for manufacturing companies?
```

### Agent Selection

| Question Type | Recommended Agent |
|---------------|-------------------|
| What is...? / Explain... | `@research` |
| How does... work? | `@research` |
| Create architecture... | `@architect` |
| Which technology...? | `@architect` |
| Create project plan... | `@pm` |
| What resources...? | `@pm` |
| What risks...? | `@pm` |

### Asking Follow-up Questions

Use context chaining for follow-up questions:

```markdown
1. @research What is D365 Finance?

2. @research What modules does it have?

3. @architect How would you integrate these modules?

4. @pm Create a plan based on the architecture
```

---

## Troubleshooting

### "No questions found"

**Problem:** No questions were recognized.

**Solution:** Make sure questions are numbered:
```markdown
# Correct
1. What is D365?
2. How does the integration work?

# Wrong
- What is D365?
* How does the integration work?
```

### "Unknown agent"

**Problem:** Agent mention was not recognized.

**Solution:** Use a valid alias:
```
@research, @res, @r
@architekt, @architect, @arch, @sa
@projektleiter, @pm, @pl, @project
```

### Rate Limit Error (429)

**Problem:** API rate limit exceeded.

**Solution:** The system waits automatically and retries the request. For frequent errors:
- Process fewer questions at once
- Longer pauses between runs
- Replace Claude Opus with Sonnet (higher limit)

### "Knowledge base is empty"

**Problem:** No documents in the knowledge base.

**Solution:**
```bash
# Import global knowledge
python main.py RAG add-knowledge -f ./d365_docs

# Import project documents
python main.py RAG addfiles -f ./project_docs -p 99
```

---

## LLM Overview

### Currently Configured Models (agents.yaml)

| Agent | Provider | Model | Context |
|-------|----------|-------|---------|
| Research | Ollama | gpt-oss:120b-cloud | 8K |
| Project Manager | OpenAI | gpt-4.1 | 1M |
| Architect | OpenAI | gpt-4.1 | 1M |
| Supervisor | OpenAI | gpt-4.1 | 1M |

---

### Anthropic Claude

| Model | Context Window | Strengths | Weaknesses |
|-------|----------------|-----------|------------|
| **Claude Opus 4.5** | 200K | Highest intelligence, complex tasks, deep reasoning | Expensive, lower rate limit |
| **Claude Sonnet 4.5** | 200K / 1M (Beta) | Best quality/cost balance, excellent for coding & agents | 1M only in Tier 4 |
| **Claude Sonnet 4** | 200K / 1M (Beta) | Fast, cost-effective, good coding capabilities | Less creative than Opus |
| **Claude Haiku 3.5** | 200K | Very fast, cheap | Less complex |

**Pricing (>200K Tokens):** Input $3→$6/MTok, Output $15→$22.50/MTok

---

### OpenAI GPT

| Model | Context Window | Strengths | Weaknesses |
|-------|----------------|-----------|------------|
| **GPT-4.1** | 1M | Huge context, best long-context performance | Expensive, slower |
| **GPT-4.1 mini** | 1M | Large context, more affordable | Less intelligent than 4.1 |
| **GPT-4o** | 128K | Multimodal, fast, good for general purpose | Context smaller than 4.1 |
| **GPT-4 Turbo** | 128K | Solid performance | Somewhat outdated |
| **GPT-4** | 8K | Proven, stable | Small context! |

---

### Ollama (Local)

| Model | Context Window | VRAM Required | Strengths | Weaknesses |
|-------|----------------|---------------|-----------|------------|
| **Llama 3.1 70B** | 128K | ~40GB | Excellent for coding, open source | High VRAM requirement |
| **Llama 3.1 8B** | 128K | ~8GB | Fast, efficient | Less intelligent |
| **Llama 3 Gradient** | 1M+ | 64GB+ | Extremely long context | Very high VRAM |
| **Mistral Large 3** | 256K | ~80GB | MoE, efficient, long context | High-end hardware only |
| **Mistral Small 3.1** | 128K | ~16GB | Good balance | - |
| **Mistral Small** | 32K | ~12GB | Fast, compact | Shorter context |

**Note:** Ollama context can be increased with `num_ctx`, but requires more VRAM.

---

### Recommendations

| Use Case | Recommended Model | Reasoning |
|----------|-------------------|-----------|
| Long question catalogs | Claude Sonnet 4 (1M), GPT-4.1 | Largest context |
| Complex architecture | Claude Opus 4.5, GPT-4.1 | Highest intelligence |
| Cost/Speed | Ollama local, Claude Haiku | Cheap/free |
