# SADify Architecture Diagram

Created: 2026-04-29  
Last updated: 2026-05-04

This diagram visualizes the MVP architecture from the SADify Google Cloud plan, updated on 2026-04-30 to include the connected wiki knowledge layer.

## Traceability Sources

This architecture diagram should be verified against:

- `docs/superpowers/development/00_development_index.md`
- `docs/superpowers/development/03_data_model_and_output_schema.md`
- `docs/superpowers/development/04_google_cloud_setup_runbook.md`
- `docs/superpowers/development/05_development_workflow.md`
- `docs/superpowers/research/2026-05-02-track-1-resource-link-analysis.md`

If the architecture changes, update the setup runbook, data schema, workflow checkpoints, and affected tests.

## MVP Runtime Architecture

```mermaid
flowchart TD
    user["Production / On-site User"] --> browser["Browser"]

    browser --> cloudrun["Cloud Run Service<br/>sadify-app"]

    subgraph cloudrun_box["Cloud Run Container"]
        ui["Streamlit UI<br/>Requirement intake, file upload,<br/>chat, SAD preview"]
        input["Input Layer<br/>Text, MD/TXT, PDF,<br/>DOCX, XLSX, CSV"]
        extract["Extraction + Normalization<br/>Convert sources into<br/>requirement context"]
        agent["SADify Analyst Agent<br/>Python + Google ADK"]
        model_router["Model Router<br/>Requirement analysis,<br/>final SAD, fallback routes"]
        completeness["Completeness Engine<br/>Score missing requirement categories"]
        linker["Requirement Linker<br/>Connect requirements, entities,<br/>workflows, decisions, sources"]
        canonical["Canonical JSON<br/>Structured project knowledge"]
        wiki["Wiki Markdown Generator<br/>YAML frontmatter + [[wiki links]]"]
        renderer["SAD Renderer<br/>Markdown/HTML preview<br/>Docs/PDF/DOCX export source"]
        tools["Tool Layer / MCP Interface<br/>Export and external actions"]

        ui --> input
        input --> extract
        extract --> agent
        agent --> model_router
        model_router --> completeness
        agent --> linker
        completeness --> canonical
        linker --> canonical
        canonical --> wiki
        canonical --> renderer
        wiki --> tools
        renderer --> tools
    end

    cloudrun --> cloudrun_box

    model_router --> vertex["Default Route<br/>Vertex AI Gemini<br/>gemini-2.5-flash"]
    model_router -. "future adapters" .-> external_models["Optional Provider Bases<br/>OpenAI, Anthropic,<br/>OpenAI-compatible, Ollama,<br/>Hugging Face"]

    canonical <--> firestore["Firestore<br/>Projects, requirements, sources,<br/>relationships, versions, exports,<br/>completeness scores"]

    tools --> docs["Google Docs API<br/>Create SAD document"]
    tools --> drive["Google Drive API<br/>Place files into project folders"]
    tools --> pdf["PDF Export<br/>Generated SAD PDF"]
    tools --> docx["DOCX Export<br/>Generated SAD Word file"]

    drive --> root_folder["Google Drive Folder<br/>SADify Generated Docs"]
    docs --> sad_folder["Project / sad<br/>Google Docs, PDF, DOCX"]
    pdf --> sad_folder
    docx --> sad_folder
    wiki --> wiki_folder["Project / wiki<br/>Obsidian-compatible Markdown files"]
    wiki_folder --> obsidian["Optional Obsidian Vault<br/>Graph view shows linked requirements"]
    sad_folder --> root_folder
    wiki_folder --> root_folder

    tools -. "Later extension" .-> github["GitHub Issues API / MCP<br/>Create developer tasks"]

    cloudrun_box --> secrets["Secret Manager<br/>GitHub token / app secrets"]

    service_account["Service Account<br/>sadify-agent-sa@sadify.iam.gserviceaccount.com"]
    service_account -. "runtime identity" .-> cloudrun
    service_account -. "Vertex AI User" .-> vertex
    service_account -. "Datastore User" .-> firestore
    service_account -. "Secret Accessor" .-> secrets
    service_account -. "Drive folder shared as Editor" .-> root_folder
```

## Wiki Knowledge Layer

SADify should generate an Obsidian-compatible Markdown wiki from the same canonical JSON used for SAD exports. This makes the project knowledge chunked, linked, and explorable.

```text
Google Drive/
  SADify Generated Docs/
    Project Name/
      sad/
        SAD-v1.google_doc
        SAD-v1.pdf
        SAD-v1.docx
      wiki/
        requirements/
          REQ-001-fertilizer-application-logging.md
          REQ-002-worker-attendance.md
        entities/
          ENT-001-worker.md
          ENT-002-field-block.md
        workflows/
          WF-001-fertilizer-recording.md
        decisions/
          DEC-001-offline-mode-needed.md
        sources/
          SRC-001-uploaded-sop.md
```

Example wiki note shape:

```markdown
---
id: REQ-001
type: requirement
status: draft
completeness: 72
confidence: medium
sources:
  - SRC-001
related:
  - REQ-002
shared_entities:
  - ENT-001
  - ENT-002
---

# Fertilizer Application Logging

## Summary
Field staff need to record fertilizer application by block, date, worker, and fertilizer type.

## Related Notes
- [[REQ-002-worker-attendance]]
- [[ENT-001-worker]]
- [[ENT-002-field-block]]
- [[WF-001-fertilizer-recording]]

## Open Questions
- [HIGH] Who verifies the fertilizer record?
- [MEDIUM] Is offline entry required in the field?
```

## Main User Flow

```mermaid
sequenceDiagram
    actor User as Production User
    participant UI as Streamlit UI
    participant Agent as SADify ADK Agent
    participant Gemini as Vertex AI Gemini
    participant Store as Firestore
    participant Wiki as Wiki Generator
    participant Docs as Docs/PDF/DOCX Export
    participant Drive as Google Drive

    User->>UI: Enter messy requirement or upload business files
    UI->>Agent: Send normalized requirement context
    Agent->>Gemini: Analyze requirement and missing info
    Gemini-->>Agent: Extracted context and gaps
    Agent->>Agent: Calculate completeness score
    Agent->>Agent: Link related requirements, entities, workflows, decisions
    Agent->>Store: Save canonical JSON and relationships

    alt Requirement incomplete
        Agent-->>UI: Ask 3-5 clarification questions
        User->>UI: Answer questions naturally
        UI->>Agent: Send clarification answers
        Agent->>Gemini: Re-analyze with answers
        Gemini-->>Agent: Updated structured requirement
        Agent->>Store: Save updated canonical JSON and relationships
    end

    Agent->>Gemini: Generate structured SAD document
    Gemini-->>Agent: SAD sections and developer tasks
    Agent->>Store: Save SAD version
    Agent->>Wiki: Generate linked Markdown wiki notes
    Wiki->>Drive: Save wiki files into project wiki folder
    Agent-->>UI: Show SAD preview
    User->>UI: Click Export
    UI->>Agent: Export request
    Agent->>Docs: Create Google Docs/PDF/DOCX outputs
    Docs->>Drive: Save outputs into project sad folder
    Drive-->>Agent: Return document and folder URLs
    Agent->>Store: Save exported_doc_url
    Agent-->>UI: Show SAD export links and wiki folder link
```

## Design Notes

- One Cloud Run service keeps the hackathon MVP simple and avoids frontend/backend deployment overhead.
- Vertex AI Gemini is the default reasoning layer; Firestore is the memory/state layer.
- SADify now has a provider-neutral model router for requirement analysis, final SAD generation, and optional fallback metadata.
- Non-Google provider adapters are future until the requirement-analysis flow exists and can test them against real SADify behavior.
- Firestore stores the canonical structured data. Markdown wiki files are generated from that structure for human navigation and Obsidian graph view.
- Google Docs, PDF, and DOCX export are normal user-facing outputs.
- The wiki knowledge layer is an MVP architecture concept, but Obsidian itself is optional. SADify only needs to generate compatible Markdown files.
- Tool boundaries should be MCP-compatible. A remote MCP server is future only; the MVP can start with clean Python tools inside the ADK agent.
- GitHub Issues export is intentionally marked as a later extension.
- `roles/run.invoker` is not required for the runtime service account when the demo service is public through `--allow-unauthenticated`.
