# SuccessForge Setup Guide

*Complete configuration guide for the AI-powered D365 FSCM implementation framework*

---

## Overview

SuccessForge requires five core components to be configured before use:

| # | Component | Purpose | Configuration File |
|---|-----------|---------|-------------------|
| A | Environment Variables | API keys and system settings | `.env` |
| B | Agent Configuration | LLM providers, models, tools | `config/agents.yaml` |
| C | Knowledge RAG | Global D365 documentation | `knowledge/` folder |
| D | Project RAG | Project-specific documents | `Projects/` folder |
| E | Question Catalogs | Structured query templates | `*.md` files |

---

## A. Environment Variables (`.env`)

The `.env` file contains API keys and configuration for all external services.

### Required API Keys

```bash
# =============================================================================
# LLM PROVIDER API KEYS
# At least one provider is required
# =============================================================================

# Anthropic Claude (for Architekt agent)
ANTHROPIC_API_KEY=sk-ant-api03-...

# OpenAI (for Projektleiter agent)
OPENAI_API_KEY=sk-proj-...

# Google (optional, for embeddings)
GOOGLE_API_KEY=AIzaSy...

# =============================================================================
# OLLAMA CONFIGURATION (Local LLM)
# Used for Research Agent by default
# =============================================================================

OLLAMA_MODEL=gpt-oss:120b-cloud
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TEMPERATURE=0.7
OLLAMA_NUM_CTX=4096

# =============================================================================
# RESEARCH TOOLS
# =============================================================================

# Tavily Search API (for web search capability)
TAVILY_API_KEY=tvly-dev-...

# =============================================================================
# AGENT SETTINGS
# =============================================================================

AGENT_MAX_ITERATIONS=10
AGENT_VERBOSE=true
```

### Obtaining API Keys

| Provider | URL | Notes |
|----------|-----|-------|
| Anthropic | https://console.anthropic.com | Claude models |
| OpenAI | https://platform.openai.com | GPT-4 models |
| Tavily | https://tavily.com | Web search API |
| Google | https://makersuite.google.com | Optional embeddings |

### Verification

```bash
# Test that environment is loaded
python -c "import dotenv; dotenv.load_dotenv(); import os; print('ANTHROPIC:', 'OK' if os.getenv('ANTHROPIC_API_KEY') else 'MISSING')"
```

---

## B. Agent Configuration (`config/agents.yaml`)

This file defines which LLM each agent uses, its tools, and behavior.

### Structure

```yaml
# =============================================================================
# AGENT CONFIGURATION
# =============================================================================
#
# Each agent has:
#   - name: Display name
#   - role: Internal role identifier
#   - role_file: Path to system prompt (relative to roles/)
#   - llm_provider: "ollama", "openai", or "claude"
#   - model: Specific model name
#   - temperature: Creativity (0.0 = deterministic, 1.0 = creative)
#   - tools: List of available tools

agents:
  # ---------------------------------------------------------------------------
  # RESEARCH AGENT
  # Purpose: Information retrieval, web search, knowledge base queries
  # ---------------------------------------------------------------------------
  research:
    name: "Research Agent"
    role: "researcher"
    role_file: "research.md"
    llm_provider: "ollama"              # Local LLM
    model: "gpt-oss:120b-cloud"
    temperature: 0.3                     # Lower = more factual
    tools:
      - "web_search"
      - "query_knowledge_base"
      - "list_projects"
      - "save_markdown"

  # ---------------------------------------------------------------------------
  # PROJEKTLEITER (Project Manager) AGENT
  # Purpose: Project planning, governance, risk management
  # ---------------------------------------------------------------------------
  projektleiter:
    name: "Projektleiter"
    role: "project_manager"
    role_file: "projektleiter.md"
    llm_provider: "openai"
    model: "gpt-4.1"
    temperature: 0.3
    tools:
      - "all"                            # Access to all tools

  # ---------------------------------------------------------------------------
  # SOLUTION ARCHITEKT AGENT
  # Purpose: Technical design, architecture, integration
  # ---------------------------------------------------------------------------
  architekt:
    name: "Solution Architekt"
    role: "architect"
    role_file: "architekt.md"
    llm_provider: "openai"
    model: "gpt-4.1"
    temperature: 0.3
    tools:
      - "query_knowledge_base"
      - "list_projects"
      - "web_search"
      - "save_markdown"

  # ---------------------------------------------------------------------------
  # SUPERVISOR AGENT
  # Purpose: Task orchestration and delegation
  # ---------------------------------------------------------------------------
  supervisor:
    name: "Supervisor"
    role: "supervisor"
    role_file: "supervisor.md"
    llm_provider: "openai"
    model: "gpt-4.1"
    temperature: 0.3
    tools:
      - "delegate_to_agent"
```

### Available Tools

| Tool | Description |
|------|-------------|
| `query_knowledge_base` | Search RAG vector database |
| `list_projects` | List available projects |
| `web_search` | Search the web via Tavily |
| `save_markdown` | Save results to Markdown file |
| `delegate_to_agent` | Delegate to another agent (Supervisor only) |
| `all` | Access to all tools |

### Role Files

System prompts are stored in `roles/` as Markdown files:

```
roles/
├── research.md           # Research Agent prompt
├── projektleiter.md      # Project Manager prompt
├── architekt.md          # Solution Architect prompt
├── supervisor.md         # Supervisor prompt
└── 01_Projektleiter_D365_FSCM.md  # Extended role description
```

---

## C. Knowledge RAG (Global Knowledge Base)

The Knowledge RAG contains D365 documentation, best practices, and methodology guides that apply to **all projects**.

### Setup Process

**Step 1: Prepare Knowledge Documents**

Place D365 documentation in the `knowledge/` folder:

```
knowledge/
├── Dynamics 365 Implementation Guide v1-2.pdf
├── Success by Design Delivery Plan DEC 2025.xlsx
├── Business Process Catalog Tree.xlsx
└── Deliverables Tree DEC 2025.xlsx
```

**Step 2: Import to Knowledge Base**

```bash
# Import all documents from knowledge/ folder
python main.py RAG knowledge-import ./knowledge/

# Force re-import (ignores hash check)
python main.py RAG knowledge-import ./knowledge/ --force
```

**Step 3: Verify Import**

```bash
# Check knowledge base status
python main.py RAG knowledge-status

# Search the knowledge base
python main.py RAG knowledge-search "Success by Design phases"
```

### Supported Document Formats

| Category | Extensions |
|----------|------------|
| Documents | `.pdf`, `.docx`, `.doc`, `.txt`, `.md` |
| Spreadsheets | `.xlsx`, `.xls`, `.csv` |
| Presentations | `.pptx`, `.ppt` |
| Data | `.json`, `.xml` |
| Web | `.html`, `.htm` |

### Knowledge Base Management

```bash
# List all documents in knowledge base
python main.py RAG knowledge-list

# Delete specific document
python main.py RAG knowledge-delete --file "outdated-guide.pdf"

# Clear entire knowledge base (use with caution!)
python main.py RAG knowledge-clear --yes
```

---

## D. Project RAG (Project-Specific Documents)

The Project RAG stores documents specific to individual implementation projects. Each project is identified by a numeric **Project ID**.

### Setup Process

**Step 1: Create Project Folder**

```bash
mkdir -p Projects/99_Contoso_D365_Finance
```

**Step 2: Add Project Documents**

```
Projects/99_Contoso_D365_Finance/
├── Requirements/
│   ├── Functional_Requirements.docx
│   └── Technical_Requirements.pdf
├── Design/
│   ├── Solution_Blueprint.docx
│   └── Integration_Architecture.pdf
├── Meetings/
│   └── Kickoff_Notes.md
└── Data/
    └── Master_Data_Mapping.xlsx
```

**Step 3: Import Project Documents**

```bash
# Import with Project ID 99
python main.py RAG import ./Projects/99_Contoso_D365_Finance/ --project 99

# Incremental update (only new/changed files)
python main.py RAG import ./Projects/99_Contoso_D365_Finance/ --project 99

# Force full re-import
python main.py RAG import ./Projects/99_Contoso_D365_Finance/ --project 99 --force
```

**Step 4: Verify Import**

```bash
# Check project status
python main.py RAG status --project 99

# Search within project
python main.py RAG search "integration requirements" --project 99
```

### Project RAG Management

```bash
# List all projects
python main.py RAG list-projects

# List files in a project
python main.py RAG list --project 99

# Delete single file from project
python main.py RAG delete --file "outdated.pdf" --project 99

# Delete entire project (use with caution!)
python main.py RAG delete --project 99 --yes
```

### Incremental Updates

The RAG system tracks file hashes for incremental updates:

| Status | Description |
|--------|-------------|
| `[NEW]` | File added to database |
| `[UPDATED]` | File changed, re-indexed |
| `[SKIPPED]` | File unchanged, skip |
| `[FAILED]` | Processing error |

---

## E. Question Catalogs (Fragenkatalog)

Question Catalogs are structured Markdown files that define a series of questions to be answered by specific agents.

### Structure

```markdown
# Project Title

## Context
[Background information that applies to ALL questions below]

## Questions

1. @agent_mention First question?

2. @agent_mention Second question?

3. Question without mention (uses default: @research)
```

### Agent Mentions

| Mention | Agent | Use For |
|---------|-------|---------|
| `@research`, `@res`, `@r` | Research Agent | Information gathering, web search |
| `@projektleiter`, `@pm`, `@pl` | Projektleiter | Planning, governance, risks |
| `@architekt`, `@arch`, `@sa` | Solution Architekt | Technical design, architecture |

### Example: Project Kickoff Catalog

```markdown
# D365 Finance Implementation - Contoso GmbH

## Context

**Company:** Contoso GmbH
**Industry:** Manufacturing
**Employees:** 850
**Current ERP:** SAP ECC 6.0 (end of support 2027)
**Target:** D365 Finance & Operations
**Budget:** 1.5M EUR
**Timeline:** 18 months

## Questions

1. @research What are the key D365 Finance modules relevant for
   manufacturing companies?

2. @architekt Design a high-level integration architecture for
   D365 Finance with the existing Salesforce CRM.

3. @pm Create a project plan with phases and milestones following
   Success by Design methodology.

4. @pm What are the top 5 risks for this project and how can
   they be mitigated?

5. @research What training approach is recommended for end users
   during an ERP transition?
```

### Processing Question Catalogs

```bash
# Process and insert answers (modifies file in place)
python main.py Agents process-file ./examples/project_kickoff.md

# Process with project context
python main.py Agents process-file ./examples/project_kickoff.md --project 99

# Dry run (show answers without writing)
python main.py Agents process-file ./examples/project_kickoff.md --dry-run

# Output to different file
python main.py Agents process-file ./examples/project_kickoff.md --output ./results/answered.md

# Enable debug mode
python main.py Agents process-file ./examples/project_kickoff.md --debug
```

### Output Format

After processing, answers are inserted below each question:

```markdown
1. @research What are the key D365 Finance modules?

**Answer (Research Agent):**

The key D365 Finance modules for manufacturing include:
- General Ledger: Core financial accounting...
- Accounts Payable/Receivable: Vendor and customer management...
- Fixed Assets: Equipment and machinery tracking...
[...]
```

---

## Quick Start Checklist

```
□ 1. Copy .env.example to .env and add API keys
□ 2. Configure agents in config/agents.yaml
□ 3. Import knowledge base documents
      python main.py RAG knowledge-import ./knowledge/
□ 4. Create project folder and import documents
      python main.py RAG import ./Projects/MyProject/ --project 1
□ 5. Test with a simple query
      python main.py Agents ask "@research What is D365 Finance?"
□ 6. Process first question catalog
      python main.py Agents process-file ./examples/d365_projekt_fragen.md --project 1
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "API key not found" | Check `.env` file exists and contains valid keys |
| "Ollama connection refused" | Ensure Ollama is running: `ollama serve` |
| "No documents found" | Run `python main.py RAG status` to verify import |
| "Unknown agent" | Check agent name in `config/agents.yaml` |
| "Rate limit exceeded" | Built-in retry with backoff; wait and retry |

### Debug Mode

```bash
# Enable verbose output for any command
python main.py Agents ask "@research Test" --debug
```

### Logs

Check `./logs/` folder for detailed processing logs.

---

*For additional support, refer to the role descriptions in `roles/` or the main documentation.*
