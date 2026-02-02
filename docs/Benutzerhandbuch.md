# Benutzerhandbuch: FSCM Multi-Agent System

## Übersicht

Das FSCM Multi-Agent System ermöglicht es, Markdown-Dateien mit Fragen automatisch durch KI-Agenten beantworten zu lassen. Die Antworten werden direkt in die Datei eingefügt. Das System unterstützt mehrere spezialisierte Agenten, eine globale Wissensdatenbank und automatisches Rate-Limit-Handling.

## Schnellstart

```bash
# Fragen beantworten und Datei aktualisieren
python main.py Agents process-file meine_fragen.md

# Vorschau ohne Änderungen (Dry-Run)
python main.py Agents process-file meine_fragen.md --dry-run

# Mit Projekt-Filter (RAG-Abfragen nur aus Projekt 99)
python main.py Agents process-file meine_fragen.md -p 99

# Mit Debug-Ausgabe (zeigt System Prompts, Messages, Tool Calls)
python main.py Agents process-file meine_fragen.md -d
```

---

## Setup-Prozess

Bevor Sie das System nutzen können, müssen folgende Schritte durchgeführt werden:

```
┌─────────────────────────────────────────────────────────────────┐
│  Setup-Reihenfolge                                              │
├─────────────────────────────────────────────────────────────────┤
│  1. .env             → API-Keys konfigurieren                   │
│  2. agents.yaml      → Agenten & LLMs konfigurieren             │
│  3. Knowledge RAG    → Globales D365-Wissen importieren         │
│  4. Project RAG      → Projektspezifische Dokumente importieren │
│  5. Fragenkatalog    → Markdown-Datei mit Fragen erstellen      │
└─────────────────────────────────────────────────────────────────┘
```

### Schritt 1: Environment-Konfiguration (.env)

Erstellen Sie eine `.env` Datei im Projektverzeichnis:

```bash
cp .env.example .env
```

**Erforderliche API-Keys:**

| Variable | Beschreibung | Erforderlich für |
|----------|--------------|------------------|
| `ANTHROPIC_API_KEY` | Anthropic Claude API | `llm_provider: claude` |
| `OPENAI_API_KEY` | OpenAI API | `llm_provider: openai` |
| `TAVILY_API_KEY` | Tavily Web-Suche | `web_search` Tool |

**Beispiel `.env`:**

```bash
# LLM Provider (mindestens einer erforderlich)
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
OPENAI_API_KEY=sk-proj-xxxxx

# Ollama (für lokale LLMs)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3

# Web-Suche
TAVILY_API_KEY=tvly-xxxxx

# Agent-Einstellungen
AGENT_MAX_ITERATIONS=10
AGENT_VERBOSE=true
```

**API-Keys erhalten:**
- Anthropic: https://console.anthropic.com/
- OpenAI: https://platform.openai.com/api-keys
- Tavily: https://tavily.com/

---

### Schritt 2: Agent-Konfiguration (config/agents.yaml)

Konfigurieren Sie die Agenten nach Ihren Bedürfnissen:

```yaml
agents:
  research:
    name: "Research Agent"
    role: "researcher"
    role_file: "de/research.md"      # Minimale Rolle (deutsch)
    # role_file: "research.md"       # Ausführliche Rolle
    # role_file: "en/research.md"    # Minimale Rolle (englisch)
    llm_provider: "ollama"           # ollama, claude, openai
    model: "llama3"                  # Modellname
    temperature: 0.3
    tools:
      - "web_search"
      - "query_knowledge_base"
      - "list_projects"
      - "save_markdown"
```

**Wichtige Entscheidungen:**

| Einstellung | Optionen | Empfehlung |
|-------------|----------|------------|
| `llm_provider` | ollama, claude, openai | `ollama` für Kosten, `openai` für Qualität |
| `role_file` | de/*.md, en/*.md, *.md | `de/` für kurze Prompts, Root für ausführliche |
| `temperature` | 0.0 - 1.0 | 0.3 für präzise, 0.7 für kreative Antworten |

---

### Schritt 3: Globale Wissensdatenbank (Knowledge RAG)

Importieren Sie allgemeines D365-Wissen, das für **alle** Projekte verfügbar sein soll:

```bash
# Ordner mit D365-Dokumentation importieren
python main.py RAG add-knowledge -f ./d365_dokumentation

# Einzelne Datei importieren
python main.py RAG add-knowledge -f ./D365_Finance_Guide.pdf

# Inhalt prüfen
python main.py RAG list-knowledge
```

**Geeignete Dokumente:**
- Microsoft D365 Dokumentation (PDFs)
- Best Practices & Lessons Learned
- Architektur-Leitfäden
- Technische Referenzen

**Ausgabe:**
```
📚 Adding to global knowledge base...
  ✅ D365_Finance_Guide.pdf (234 chunks)
  ✅ Integration_Best_Practices.md (56 chunks)
  ✅ Data_Migration_Handbook.pdf (189 chunks)
```

---

### Schritt 4: Projekt-Wissensdatenbank (Project RAG)

Importieren Sie projektspezifische Dokumente mit einer `project_id`:

```bash
# Projekt-Dokumente importieren (Projekt-ID: 99)
python main.py RAG addfiles -f ./projekt_99_docs -p 99

# Weiteres Projekt
python main.py RAG addfiles -f ./projekt_100_docs -p 100

# Projekt-Dokumente anzeigen
python main.py RAG delete --project 99 --dry-run
```

**Geeignete Dokumente:**
- Anforderungsdokumente
- Lastenheft / Pflichtenheft
- Projektpläne
- Architektur-Diagramme
- Meeting-Protokolle

**Ausgabe:**
```
📁 Adding to project 99...
  ✅ Anforderungen.pdf (123 chunks)
  ✅ Lastenheft_v2.docx (89 chunks)
  ✅ Architektur_Entwurf.md (45 chunks)
```

---

### Schritt 5: Fragenkatalog erstellen

Erstellen Sie eine Markdown-Datei mit Ihren Fragen:

```markdown
# Projektname: D365 Finance Einführung

## Kontext

### Unternehmen
- Branche: Fertigung
- Mitarbeiter: 500
- Standorte: 3 (DACH-Region)

### Ausgangssituation
- Aktuelles ERP: SAP R/3 (15 Jahre alt)
- Probleme: Performance, keine Cloud-Anbindung
- Budget: 500.000 EUR
- Zeitrahmen: 12 Monate

### Ziele
- Migration auf D365 Finance & SCM
- Integration mit bestehendem CRM (Salesforce)
- Automatisierung der Lagerverwaltung

---

## Fragen

1. @research Was sind die Hauptunterschiede zwischen SAP R/3 und D365 Finance?

2. @research Welche D365-Module sind für ein Fertigungsunternehmen relevant?

3. @architekt Erstelle eine High-Level-Architektur für die D365-Salesforce-Integration

4. @architekt Welche Datenmigrationsstrategie empfiehlst du für die SAP-Migration?

5. @pm Erstelle einen Projektplan mit Meilensteinen für die 12-monatige Einführung

6. @pm Welche Ressourcen und Rollen werden für das Projekt benötigt?

7. @research Welche Risiken gibt es bei einer SAP-zu-D365-Migration?

8. @pm Erstelle eine Risikomatrix basierend auf den identifizierten Risiken
```

**Ausführen:**

```bash
# Dry-Run (Vorschau)
python main.py Agents process-file projekt_fragen.md --dry-run -p 99

# Tatsächlich ausführen
python main.py Agents process-file projekt_fragen.md -p 99

# Mit Debug-Ausgabe
python main.py Agents process-file projekt_fragen.md -p 99 -d
```

---

### Setup verifizieren

Prüfen Sie, ob alles korrekt konfiguriert ist:

```bash
# 1. Agenten auflisten
python main.py Agents list-agents

# 2. Wissensdatenbank prüfen
python main.py RAG list-knowledge

# 3. Test-Frage stellen
python main.py Agents ask "@research Was ist D365 Finance?" -p 99

# 4. Chat-Modus testen
python main.py Agents chat -p 99
```

**Erwartete Ausgabe (list-agents):**
```
Available Agents:

research
  Name: Research Agent
  Role: researcher
  LLM: ollama / llama3
  Tools: web_search, query_knowledge_base, list_projects, save_markdown
  Mentions: @research, @res, @r

architekt
  Name: Solution Architekt
  Role: architect
  LLM: openai / gpt-4.1
  ...
```

---

## Markdown-Format

### Grundstruktur

Eine Eingabedatei besteht aus zwei Teilen:

1. **Kontext** - Alles vor der ersten nummerierten Frage
2. **Fragen** - Nummerierte Liste mit optionalen @Agent-Mentions

### Beispiel-Eingabedatei

```markdown
# Projektname: D365 Finance Integration

## Hintergrund
Das Unternehmen möchte seine bestehende ERP-Lösung durch
Microsoft Dynamics 365 Finance ersetzen. Die Integration
mit dem bestehenden CRM-System ist erforderlich.

## Budget
500.000 EUR

## Zeitrahmen
12 Monate

1. @research Was sind die Hauptfunktionen von D365 Finance?

2. @architekt Wie sollte die Integration mit dem CRM aufgebaut werden?

3. @pm Erstelle einen groben Projektplan für die Einführung

4. Welche Risiken gibt es bei der Migration?
```

### Regeln für das Format

| Element | Regel |
|---------|-------|
| **Kontext** | Beliebiger Text vor der ersten nummerierten Frage |
| **Fragen** | Müssen nummeriert sein: `1.`, `2.`, `3.` usw. |
| **@Mention** | Optional, bestimmt den Agenten (Standard: research) |
| **Fragetext** | Beliebiger Text nach der Nummer (und optional @Mention) |

---

## Ausgabeformat

Nach der Verarbeitung werden die Antworten direkt unter den Fragen eingefügt.
**Die Fragen werden als Überschriften formatiert und der @agent-Teil wird entfernt:**

### Vorher (Eingabe)

```markdown
# Projekt

Kontext zum Projekt...

1. @research Was ist D365?

2. @pm Erstelle einen Zeitplan
```

### Nachher (Ausgabe)

```markdown
# Projekt

Kontext zum Projekt...

### Was ist D365?

Microsoft Dynamics 365 ist eine Suite von
Enterprise-Anwendungen, die ERP- und CRM-Funktionalitäten
kombiniert...

### Erstelle einen Zeitplan

Basierend auf dem Projektkontext empfehle ich
folgenden Zeitplan:
- Phase 1: Analyse (4 Wochen)
- Phase 2: Design (6 Wochen)
...
```

### Inkrementelles Schreiben

Die Ausgabedatei wird **nach jeder beantworteten Frage** geschrieben, nicht erst am Ende. So können Sie:
- Den Fortschritt live verfolgen
- Bei Abbruch bereits beantwortete Fragen behalten
- Lange Verarbeitungen jederzeit unterbrechen

### Kontext-Verkettung

Nachfolgende Fragen erhalten automatisch **alle** vorherigen Antworten als Kontext. So können Sie sich auf vorherige Antworten beziehen:

```markdown
1. @research Was ist D365 Finance?

2. @research Erkläre das genauer  # Bezieht sich auf Antwort 1

3. @pm Basierend auf den Informationen, erstelle einen Plan  # Bezieht sich auf Antworten 1+2
```

---

## Verfügbare Agenten

Die Agenten können über Konfigurationsdateien angepasst werden. Siehe Abschnitt [Agent-Konfiguration](#agent-konfiguration) für Details.

### @research (Standard)

**Aliases:** `@research`, `@res`, `@r`

Der Research-Agent ist spezialisiert auf:
- Faktenrecherche
- Informationssammlung
- Wissensbasis-Abfragen

**LLM:** Ollama (lokal)

**Beispiel:**
```markdown
1. @research Was ist Microsoft Dynamics 365?
1. @res Welche Module gibt es in D365 Finance?
1. @r Erkläre den Unterschied zwischen D365 Finance und Business Central
```

### @architekt

**Aliases:** `@architekt`, `@architect`, `@arch`, `@sa`

Der Solution Architekt ist spezialisiert auf:
- Technische Architektur
- Integrationsdesign
- Systemlandschaften
- Best Practices

**LLM:** Claude Sonnet

**Beispiel:**
```markdown
2. @architekt Erstelle eine Integrationsarchitektur für D365 und Salesforce
2. @arch Welche API-Strategie empfiehlst du?
2. @sa Wie sollte die Datenmigration strukturiert werden?
```

### @projektleiter

**Aliases:** `@projektleiter`, `@pm`, `@pl`, `@project`

Der Projektleiter ist spezialisiert auf:
- Projektplanung
- Ressourcenmanagement
- Risikobewertung
- Meilensteine

**LLM:** Claude Sonnet

**Beispiel:**
```markdown
3. @pm Erstelle einen Projektplan für die D365-Einführung
3. @projektleiter Welche Ressourcen werden benötigt?
3. @pl Identifiziere die kritischen Meilensteine
```

---

## Wissensdatenbank

Das System verwendet zwei separate Wissensdatenbanken:

### Projekt-Wissensbasis (rag_collection)

Projektspezifische Dokumente mit `project_id`:

```bash
# Dokumente zu Projekt 99 importieren
python main.py RAG addfiles -f ./projekt_docs -p 99

# Projekt-Dokumente anzeigen
python main.py RAG delete --project 99 --dry-run
```

### Globale Wissensdatenbank (knowledge_base)

Allgemeines Wissen (D365 Doku, Best Practices, etc.) **ohne** project_id:

```bash
# Globales Wissen importieren
python main.py RAG add-knowledge -f ./d365_documentation

# Inhalt anzeigen
python main.py RAG list-knowledge

# Löschen
python main.py RAG delete-knowledge --file "D365_Guide.pdf"
python main.py RAG delete-knowledge --all
```

### Automatische kombinierte Suche

Bei jeder RAG-Abfrage werden **BEIDE** Datenbanken durchsucht:

```
Abfrage: "Was ist D365 Finance?"
    │
    ├──► Suche in rag_collection (Projekt) → 3 Ergebnisse
    │
    ├──► Suche in knowledge_base (Global) → 2 Ergebnisse
    │
    └──► Kombinierte Antwort: 5 Ergebnisse
```

**Beispiel-Output:**
```
[1] [Projekt 99] Anforderungen.pdf
Die Anforderungen für das System sind...

---

[2] [Projekt 99] Timeline.xlsx
Der Zeitplan sieht vor...

---

[3] [Wissensdatenbank] D365_Finance_Guide.pdf
D365 Finance ist ein ERP-Modul für...
```

---

## CLI-Befehle

### Markdown-Verarbeitung

```bash
python main.py Agents process-file <DATEI> [OPTIONEN]
```

| Option | Kurz | Beschreibung |
|--------|------|--------------|
| `--project` | `-p` | Filtert RAG-Abfragen auf ein bestimmtes Projekt |
| `--debug` | `-d` | Zeigt Debug-Ausgabe (System Prompt, Messages, Tool Calls) |
| `--dry-run` | `--dry` | Zeigt Antworten an, ohne die Datei zu ändern |
| `--output` | `-o` | Schreibt in eine andere Datei statt das Original zu überschreiben |

### RAG-Befehle

```bash
# Projekt-Dokumente
python main.py RAG addfiles -f <ORDNER> -p <PROJEKT_ID>
python main.py RAG delete --project <PROJEKT_ID>
python main.py RAG delete --file <DATEINAME>

# Globale Wissensdatenbank
python main.py RAG add-knowledge -f <ORDNER>
python main.py RAG list-knowledge
python main.py RAG delete-knowledge --file <DATEINAME>
python main.py RAG delete-knowledge --all
```

### Agent-Befehle

```bash
# Einzelne Frage stellen
python main.py Agents ask "@research Was ist D365?" -p 99
python main.py Agents ask "@architekt Erstelle eine Architektur" -d

# Agenten auflisten
python main.py Agents list-agents

# Orchestrierung (Supervisor delegiert)
python main.py Agents orchestrate "Analysiere das Projekt"

# Interaktiver Chat-Modus
python main.py Agents chat -p 99
python main.py Agents chat -p 99 -d  # Mit Debug-Ausgabe
```

---

## Interaktiver Chat-Modus

Der Chat-Modus ermöglicht eine interaktive Unterhaltung mit den Agenten. Der Chat-Verlauf wird automatisch als Kontext an nachfolgende Fragen übergeben.

### Starten

```bash
python main.py Agents chat -p 99
```

### Funktionsweise

```
🚀 FSCM Chat Mode
📁 Projekt: 99
💡 Agenten: @research, @architekt, @pm (Standard: research)
💡 Befehle: exit, clear, help

You: @research Was ist D365 Finance?

🔧 Research:
Microsoft Dynamics 365 Finance ist ein ERP-Modul für...

You: Erkläre das genauer

🔧 Research:
Basierend auf meiner vorherigen Antwort möchte ich ergänzen...

You: @architekt Wie würdest du das implementieren?

🔧 Architekt:
Basierend auf den Informationen zu D365 Finance empfehle ich...

You: clear
🗑️ Chat-Verlauf gelöscht.

You: exit
👋 Chat beendet.
```

### Chat-Befehle

| Befehl | Beschreibung |
|--------|--------------|
| `exit` | Chat beenden |
| `clear` | Chat-Verlauf löschen (Kontext wird zurückgesetzt) |
| `help` | Hilfe anzeigen |
| `Ctrl+C` | Chat sofort beenden |

### Kontext-Verkettung

Der Chat-Verlauf wird automatisch als Kontext an jede neue Frage angehängt. So können Sie:
- Auf vorherige Antworten Bezug nehmen
- Folgefragen stellen ohne Wiederholung
- Zwischen Agenten wechseln (der Kontext bleibt erhalten)

---

## Rate-Limit-Handling

Das System behandelt API-Rate-Limits (429-Fehler) automatisch:

```
Frage 1 → OK
Frage 2 → OK
...
Frage 26 → 429 Error
         → "⏳ Rate limit (429) - warte 60s vor Retry..."
         → [60 Sekunden Pause]
         → Retry → OK
Frage 27 → OK
```

**Konfiguration:**
- Max. 3 Retries
- Exponentielles Backoff: 60s → 120s → 240s (max. 5 min)
- Meldung erscheint auch ohne Debug-Mode

**Kontext-Übergabe:**
- Alle vorherigen Antworten werden als Kontext an nachfolgende Fragen übergeben
- Bei sehr vielen Fragen kann dies zu großen Token-Mengen führen

---

## Projekt-Filter

Mit dem `--project` / `-p` Parameter können RAG-Abfragen auf ein bestimmtes Projekt eingeschränkt werden.

### Verwendung

```bash
# Nur Dokumente aus Projekt 99 durchsuchen
python main.py Agents process-file fragen.md -p 99
```

### Funktionsweise

Wenn ein Projekt-Filter aktiv ist:
1. Projekt-Dokumente werden mit dem Filter durchsucht
2. Die **globale Wissensdatenbank wird IMMER zusätzlich** durchsucht
3. Beide Ergebnisse werden kombiniert

| Situation | Empfehlung |
|-----------|------------|
| Fragen zu einem bestimmten Projekt | `-p <projekt_id>` verwenden |
| Allgemeine Fragen zu D365 | Keinen Filter verwenden |
| Vergleich zwischen Projekten | Keinen Filter verwenden |

---

## Debug-Modus

Der Debug-Modus zeigt detaillierte Informationen über die Agent-Ausführung an.

### Verwendung

```bash
python main.py Agents process-file fragen.md -d
```

### Ausgabe im Debug-Modus

| Information | Beschreibung |
|-------------|--------------|
| **System Prompt** | Der vollständige System Prompt des Agents |
| **User Query** | Die an den Agent gesendete Anfrage (Kontext + Frage) |
| **Available Tools** | Liste der verfügbaren Tools |
| **Iteration X** | Jeder LLM-Aufruf |
| **LLM Response** | Die Antwort des LLMs |
| **Tool Call** | Welches Tool mit welchen Argumenten aufgerufen wird |
| **Tool Result** | Das Ergebnis des Tool-Aufrufs |
| **Rate Limit** | Informationen zu Rate-Limit-Retries |

---

## Agent-Konfiguration

Die Agenten sind vollständig konfigurierbar über zwei Arten von Dateien:

### Verzeichnisstruktur

```
FSCMV3/
├── config/
│   └── agents.yaml         # LLM-Konfiguration (Provider, Model, Tools, Role-File)
├── roles/
│   ├── research.md         # System Prompt (ausführlich)
│   ├── projektleiter.md    # System Prompt (ausführlich)
│   ├── architekt.md        # System Prompt (ausführlich)
│   ├── supervisor.md       # System Prompt (ausführlich)
│   ├── de/                 # Minimale deutsche Rollen
│   │   ├── research.md
│   │   ├── projektleiter.md
│   │   ├── architekt.md
│   │   └── supervisor.md
│   └── en/                 # Minimale englische Rollen
│       ├── research.md
│       ├── project_manager.md
│       ├── architect.md
│       └── supervisor.md
```

### LLM-Konfiguration (config/agents.yaml)

```yaml
agents:
  research:
    name: "Research Agent"
    role: "researcher"
    role_file: "de/research.md"      # Pfad relativ zu roles/
    llm_provider: "ollama"           # ollama, claude, openai
    model: "gpt-oss:120b-cloud"
    temperature: 0.3
    tools:
      - "web_search"
      - "query_knowledge_base"
      - "list_projects"
      - "save_markdown"

  projektleiter:
    name: "Projektleiter"
    role: "project_manager"
    role_file: "de/projektleiter.md"
    llm_provider: "openai"
    model: "gpt-4.1"
    temperature: 0.3
    tools:
      - "all"

  architekt:
    name: "Solution Architekt"
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

### Role-File Konfiguration

Das `role_file` Feld bestimmt, welche Markdown-Datei als System-Prompt verwendet wird:

| Wert | Pfad | Beschreibung |
|------|------|--------------|
| `"research.md"` | `roles/research.md` | Ausführlicher System-Prompt (~1700 Zeilen) |
| `"de/research.md"` | `roles/de/research.md` | Minimaler System-Prompt auf Deutsch (~25 Zeilen) |
| `"en/research.md"` | `roles/en/research.md` | Minimaler System-Prompt auf Englisch (~25 Zeilen) |

**Wenn `role_file` nicht angegeben ist**, wird automatisch `<agent_name>.md` verwendet.

**Beispiel für englische Agenten:**

```yaml
agents:
  research:
    role_file: "en/research.md"    # English minimal role
  architekt:
    role_file: "en/architect.md"   # English minimal role
  projektleiter:
    role_file: "en/project_manager.md"  # English minimal role
```

### Verfügbare LLM-Provider

| Provider | Beschreibung | Beispiel-Modelle |
|----------|--------------|------------------|
| `ollama` | Lokale LLMs via Ollama | `llama3`, `mistral`, `gpt-oss:120b-cloud` |
| `claude` | Anthropic Claude API | `claude-sonnet-4-20250514` |
| `openai` | OpenAI API | `gpt-4`, `gpt-4-turbo` |

### Verfügbare Tools

| Tool | Beschreibung |
|------|--------------|
| `query_knowledge_base` | Durchsucht Projekt-Wissensbasis + Globale Wissensdatenbank |
| `list_projects` | Listet alle Projekte in der Wissensbasis |
| `web_search` | Web-Suche via Tavily |
| `save_markdown` | Speichert Ergebnisse als Markdown-Datei |
| `all` | Zugriff auf alle verfügbaren Tools |

---

## save_markdown Tool

Das `save_markdown` Tool ermöglicht es Agenten, Ergebnisse als Markdown-Dateien zu speichern.

### Verwendung

Bitten Sie den Agenten, das Ergebnis zu speichern:

```
You: @research Recherchiere D365 Finance Features und speichere das Ergebnis

🔧 Research:
[Recherchiert und ruft save_markdown Tool auf]
✅ Saved to /Users/.../outputs/d365_finance_features.md
```

Oder mit explizitem Dateinamen:

```
You: @architekt Erstelle eine Architektur und speichere sie als api_architektur.md
```

### Parameter

| Parameter | Beschreibung | Standard |
|-----------|--------------|----------|
| `filename` | Dateiname (mit oder ohne .md) | - |
| `content` | Der zu speichernde Inhalt | - |
| `folder` | Zielordner | `./outputs` |

### Ausgabe-Format

Die gespeicherten Dateien enthalten einen Timestamp-Header:

```markdown
<!-- Generated: 2025-02-02T14:30:00.000000 -->

# D365 Finance Features

...
```

### Zugewiesen an

- `research` - Recherche-Ergebnisse speichern
- `architekt` - Architektur-Dokumente speichern
- `projektleiter` - Hat `all` Tools (automatisch enthalten)

### System Prompts (roles/*.md)

Jeder Agent hat eine eigene Markdown-Datei für seinen System Prompt:

**Beispiel: roles/research.md**

```markdown
# Research Agent

Du bist ein Research-Spezialist für D365 Finance and Supply Chain Management.

## Hauptaufgaben

- Recherche von Informationen zu D365 FSCM Features
- Durchsuchen der Wissensdatenbank
- Web-Recherche für aktuelle Dokumentation

## Anweisungen

Antworte immer auf Deutsch und strukturiere deine Ergebnisse klar.
```

---

## Tipps & Best Practices

### Kontext optimieren

Je mehr relevanter Kontext, desto bessere Antworten:

```markdown
# Projekt: ERP-Migration

## Unternehmensprofil
- Branche: Fertigung
- Mitarbeiter: 500
- Standorte: 3 (Deutschland, Österreich, Schweiz)

## Aktuelle Situation
- Legacy ERP: SAP R/3
- Alter: 15 Jahre
- Hauptprobleme: Performance, fehlende Cloud-Anbindung

1. @research Welche D365-Module sind für Fertigungsunternehmen relevant?
```

### Agent-Auswahl

| Fragetyp | Empfohlener Agent |
|----------|-------------------|
| Was ist...? / Erkläre... | `@research` |
| Wie funktioniert...? | `@research` |
| Erstelle Architektur... | `@architekt` |
| Welche Technologie...? | `@architekt` |
| Erstelle Projektplan... | `@pm` |
| Welche Ressourcen...? | `@pm` |
| Welche Risiken...? | `@pm` |

### Folgefragen stellen

Nutzen Sie die Kontext-Verkettung für Folgefragen:

```markdown
1. @research Was ist D365 Finance?

2. @research Welche Module hat es?

3. @architekt Wie würdest du diese Module integrieren?

4. @pm Erstelle einen Plan basierend auf der Architektur
```

---

## Fehlerbehebung

### "No questions found"

**Problem:** Keine Fragen wurden erkannt.

**Lösung:** Stellen Sie sicher, dass Fragen nummeriert sind:
```markdown
# Richtig
1. Was ist D365?
2. Wie funktioniert die Integration?

# Falsch
- Was ist D365?
* Wie funktioniert die Integration?
```

### "Unknown agent"

**Problem:** Agent-Mention wurde nicht erkannt.

**Lösung:** Verwenden Sie einen gültigen Alias:
```
@research, @res, @r
@architekt, @architect, @arch, @sa
@projektleiter, @pm, @pl, @project
```

### Rate Limit Error (429)

**Problem:** API-Rate-Limit überschritten.

**Lösung:** Das System wartet automatisch und wiederholt die Anfrage. Bei häufigen Fehlern:
- Weniger Fragen auf einmal verarbeiten
- Längere Pausen zwischen Durchläufen
- Claude Opus durch Sonnet ersetzen (höheres Limit)

### "Knowledge base is empty"

**Problem:** Keine Dokumente in der Wissensdatenbank.

**Lösung:**
```bash
# Globales Wissen importieren
python main.py RAG add-knowledge -f ./d365_docs

# Projekt-Dokumente importieren
python main.py RAG addfiles -f ./projekt_docs -p 99
```

---

## LLM-Übersicht

### Aktuell konfigurierte Modelle (agents.yaml)

| Agent | Provider | Modell | Kontext |
|-------|----------|--------|---------|
| Research | Ollama | gpt-oss:120b-cloud | 8K |
| Projektleiter | OpenAI | gpt-4.1 | 1M |
| Architekt | OpenAI | gpt-4.1 | 1M |
| Supervisor | OpenAI | gpt-4.1 | 1M |

---

### Anthropic Claude

| Modell | Kontext-Fenster | Stärken | Schwächen |
|--------|-----------------|---------|-----------|
| **Claude Opus 4.5** | 200K | Höchste Intelligenz, komplexe Aufgaben, tiefes Reasoning | Teuer, niedrigeres Rate-Limit |
| **Claude Sonnet 4.5** | 200K / 1M (Beta) | Beste Balance Qualität/Kosten, sehr gut für Coding & Agents | 1M nur in Tier 4 verfügbar |
| **Claude Sonnet 4** | 200K / 1M (Beta) | Schnell, kosteneffizient, gute Coding-Fähigkeiten | Weniger kreativ als Opus |
| **Claude Haiku 3.5** | 200K | Sehr schnell, günstig | Weniger komplex |

**Preise (>200K Tokens):** Input $3→$6/MTok, Output $15→$22.50/MTok

---

### OpenAI GPT

| Modell | Kontext-Fenster | Stärken | Schwächen |
|--------|-----------------|---------|-----------|
| **GPT-4.1** | 1M | Riesiger Kontext, beste Long-Context Performance | Teuer, langsamer |
| **GPT-4.1 mini** | 1M | Großer Kontext, kostengünstiger | Weniger intelligent als 4.1 |
| **GPT-4o** | 128K | Multimodal, schnell, gut für Allzweck | Kontext kleiner als 4.1 |
| **GPT-4 Turbo** | 128K | Solide Performance | Etwas veraltet |
| **GPT-4** | 8K | Bewährt, stabil | Kleiner Kontext! |

---

### Ollama (Lokal)

| Modell | Kontext-Fenster | VRAM benötigt | Stärken | Schwächen |
|--------|-----------------|---------------|---------|-----------|
| **Llama 3.1 70B** | 128K | ~40GB | Sehr gut für Coding, Open Source | Hoher VRAM-Bedarf |
| **Llama 3.1 8B** | 128K | ~8GB | Schnell, effizient | Weniger intelligent |
| **Llama 3 Gradient** | 1M+ | 64GB+ | Extrem langer Kontext | Sehr hoher VRAM |
| **Mistral Large 3** | 256K | ~80GB | MoE, effizient, langer Kontext | Nur High-End Hardware |
| **Mistral Small 3.1** | 128K | ~16GB | Gute Balance | - |
| **Mistral Small** | 32K | ~12GB | Schnell, kompakt | Kürzerer Kontext |

**Hinweis:** Ollama-Kontext kann mit `num_ctx` erhöht werden, benötigt aber mehr VRAM.

---

### Empfehlungen

| Anwendungsfall | Empfohlenes Modell | Begründung |
|----------------|-------------------|------------|
| Lange Fragenkataloge | Claude Sonnet 4 (1M), GPT-4.1 | Größter Kontext |
| Komplexe Architektur | Claude Opus 4.5, GPT-4.1 | Höchste Intelligenz |
| Kosten/Geschwindigkeit | Ollama lokal, Claude Haiku | Günstig/kostenlos |
