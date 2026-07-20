# Track 1 Resource Link Analysis

Date: 2026-05-02  
Last updated: 2026-05-04  
Scope: Google for Startups AI Agents Challenge, Track 1 only  
Local guide reviewed: `docs/sources/ai_agents_challenge_designed_guide.pdf`

## Purpose

This file tracks the source links from the challenge guide so SADify development can stay aligned with the hackathon resources without needing every page clipped into Obsidian first.

Use this file as the source checklist before coding, cloud setup, or tool changes.

## Direct Reading Decision

Current approach:

```text
Read public docs and GitHub links directly.
Create local Markdown notes for tracking and decisions.
Ask the user for screenshots or Obsidian clips only when a page is login-only, blocked, or project-specific.
```

Obsidian clipping is useful for:

- Google Cloud Console pages inside the user's logged-in project
- pages that redirect, block, or render poorly through direct reading
- pages that need to be frozen as evidence
- important source pages that may change later

## Track 1 Guide Summary

The guide defines Track 1 as building net-new agents from a blank canvas and complex business problem.

Track 1 expects participants to use:

- Agent Development Kit (ADK), or another agent framework such as LangChain or CrewAI
- Gemini Enterprise Agent Platform / Google Cloud agent tools
- Model Context Protocol (MCP) or tool integrations for external actions
- templates, examples, or starter tooling to bootstrap quickly
- local testing before deployment
- cloud deployment path when demo-ready

For SADify, the strongest interpretation is:

```text
Build an ADK-compatible Python agent.
Use Gemini for reasoning.
Expose file, wiki, export, and storage actions as clean tools.
Use Cloud Run for the prototype demo runtime.
Keep Agent Runtime / Agent Engine as optional stretch unless the hackathon submission specifically rewards or requires it.
```

## Source Link Inventory

| Source | Link | Access Status | Track 1 Relevance | SADify Decision |
| --- | --- | --- | --- | --- |
| Google Cloud home | <https://cloud.google.com/> | Public | Account/project setup | Already covered by setup runbook |
| Agent Platform console link from PDF | <https://pantheon.corp.google.com/agent-platform/overview?project=genai-on-vertex-playground> | Not reliable publicly; console/auth/project-specific | Shows Agent Platform entry point | User screenshots needed for verification |
| ADK Python repo | <https://github.com/google/adk-python> | Public | Primary Python ADK source | Use ADK-compatible Python structure |
| Agents CLI repo | <https://github.com/google/agents-cli> | Public | Current scaffold/eval/deploy helper | Check before scaffolding; preferred over old starter pack for tool-guided setup |
| Agent Starter Pack repo | <https://github.com/GoogleCloudPlatform/agent-starter-pack> | Public | Older templates and production patterns | Background only; repo itself says future development happens in Agents CLI |
| Awesome ADK Agents | <https://github.com/Sri-Krishna-V/awesome-adk-agents> | Public | Community examples and patterns | Inspiration only; not an authoritative source |
| Official ADK overview | <https://docs.cloud.google.com/agent-builder/agent-development-kit/overview> | Public; redirects to Agent Platform ADK docs | Official ADK positioning | Confirms ADK for build/debug/deploy and Cloud Run/Runtime/GKE options |
| Agent Platform ADK + Agents CLI quickstart | <https://docs.cloud.google.com/gemini-enterprise-agent-platform/agents/quickstart-adk> | Public | Shows ADK + Agents CLI lifecycle | Use as scaffold/eval/deploy reference before coding |
| Cloud Run AI agents docs | <https://docs.cloud.google.com/run/docs/ai-agents> | Public | Supports Cloud Run as agent host | Confirms Cloud Run is valid for hosting agent services |
| Cloud Run ADK deployment guide | <https://docs.cloud.google.com/run/docs/ai/build-and-deploy-ai-agents/deploy-adk-agent> | Public | Shows ADK agent shape and `root_agent` | Align local project structure with this guide |
| Cloud Run MCP server guide | <https://docs.cloud.google.com/run/docs/host-mcp-servers> | Public | MCP hosting and auth patterns | Future reference if SADify exposes remote MCP server |
| Agent Runtime / Agent Engine overview | <https://docs.cloud.google.com/agent-builder/agent-engine/overview> | Public; redirects to Agent Platform scale docs | Managed runtime, sessions, memory, observability | Stretch/future for MVP due cost/complexity |
| Agent Runtime ADK quickstart | <https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/runtime/quickstart-adk> | Public | Managed runtime deployment path | Do not use first unless deliberately moving from Cloud Run to Agent Runtime |
| ADK MCP tools docs | <https://adk.dev/tools-custom/mcp-tools/> | Public | Explains ADK + MCP patterns | Keep SADify tool layer MCP-compatible |
| ADK sessions/state/memory docs | <https://adk.dev/sessions/> | Public | Explains session/state/memory concepts | Firestore remains canonical MVP store; ADK session concepts inform design |
| Vertex AI Gemini model lifecycle | <https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions> | Public | Current stable model selection | `gemini-2.5-flash` remains a safe MVP default |
| Gemini 2.5 Flash model page | <https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/2-5-flash> | Public | Model capability and region evidence | Supports model choice; verify region in console before first cloud call |
| Grounding with Google Search | <https://docs.cloud.google.com/vertex-ai/generative-ai/docs/grounding/grounding-with-google-search> | Public | Public grounding option | Future only; not needed for SADify MVP unless demo needs live public facts |
| Vertex AI Search / Agent Search repo | <https://github.com/GoogleCloudPlatform/generative-ai/tree/main/search> | Public | RAG/search examples | Future only; local uploads + Firestore/wiki are enough for MVP |
| RAG codelab | <https://codelabs.developers.google.com/build-google-quality-rag> | Public | RAG with uploaded corpus and Cloud Run | Future only; useful if SADify later needs larger document knowledge base |

## Important Findings

### 1. SADify Is On The Right Track

The current SADify plan matches Track 1 because it is a net-new agent, uses ADK, uses Gemini, connects to tools, and solves a real business workflow problem.

No major architecture reversal is needed.

### 2. Agents CLI Should Be Checked Before Scaffolding

The guide points to Agents CLI, and the current public docs position it as the newer lifecycle helper for scaffolding, local testing, evaluation, deployment, and observability.

Decision:

```text
Before writing the first project scaffold manually, check Agents CLI and decide whether to:
1. scaffold with Agents CLI, then adapt for SADify, or
2. build manually but follow the ADK-compatible structure.
```

### 3. Agent Starter Pack Is Now Background, Not The First Choice

The Agent Starter Pack repo says future development happens in Agents CLI.

Decision:

```text
Use Agent Starter Pack as reference only.
Do not treat it as the primary starting tool unless Agents CLI fails or is too heavy.
```

### 4. Cloud Run Is Valid For MVP

Cloud Run docs explicitly support hosting AI agents and ADK agents. This supports the current plan to deploy one demo-ready service after local checkpoints pass.

Decision:

```text
Keep Cloud Run as the MVP deployment target.
Do not move to GKE for the prototype.
Do not move to Agent Runtime unless there is a clear hackathon/demo reason.
```

### 5. Agent Runtime Is A Stretch Path

Agent Platform Runtime offers managed scaling, sessions, memory, and observability, but the quickstart introduces extra setup such as staging buckets and managed runtime resources.

Decision:

```text
Use Cloud Run first.
Keep Agent Runtime / Agent Engine as future or stretch unless required by the final submission strategy.
```

### 6. MCP Alignment Matters

Track 1 emphasizes MCP/tool integrations. ADK supports MCP tool integration through `McpToolset`, and Cloud Run can host remote MCP servers.

Decision:

```text
For MVP, implement SADify actions as clean Python tools:
- extract source files
- update canonical JSON
- generate wiki Markdown
- verify wiki drafts
- export Google Docs/PDF/DOCX

Make the tool boundaries clean enough to wrap as MCP later.
```

### 7. RAG/Search Is Not Required For MVP

The guide includes Agent Search, grounding, and RAG resources, but SADify's MVP can rely on uploaded files, canonical JSON, Firestore, and wiki Markdown.

Decision:

```text
Do not add Vertex AI Search, RAG Engine, BigQuery, Cloud Storage corpus ingestion, or Vector Search to the MVP.
Mark them as future only if the local file/wiki memory becomes insufficient.
```

### 8. Gemini 2.5 Flash Still Makes Sense

The Gemini model lifecycle page lists `gemini-2.5-flash` as a latest stable model, and the Gemini 2.5 Flash page describes it as strong for price/performance.

Decision:

```text
Use `gemini-2.5-flash` first.
Use Pro only for final SAD generation if output quality is weak.
Do not switch to Gemini 3 preview models just because they appear in the console unless we deliberately verify stability, pricing, region, and ADK support.
```

2026-05-04 implementation note:

```text
SADify now has provider-neutral route metadata, but `google / gemini-2.5-flash` remains the default route for Track 1. Non-Google live adapters are future until requirement analysis exists.
```

### 9. Budget Amount Must Follow Actual Project Budget

The guide text says eligible startups may receive USD 500 credits. SADify planning must follow the user's actual current Google Cloud budget guardrail.

Decision:

```text
Current confirmed guardrail: <budget-guardrail> billing-account budget with actual-spend alerts at 25%, 50%, 75%, and 90%.
Recommended before heavy model/deploy loops: smaller project-only prototype budget around <prototype-budget>.
Treat USD 500 as guide context only, not the actual project budget.
```

## Alignment Against Current SADify Docs

| Current Doc Area | Status | Notes |
| --- | --- | --- |
| Track 1 positioning | Aligned | SADify is a net-new business workflow agent |
| ADK framework choice | Aligned | Keep ADK-compatible Python agent core |
| Gemini model choice | Aligned | `gemini-2.5-flash` remains safe first choice and current default route |
| Flexible model routing | Aligned with caution | Route metadata is acceptable; Google/Gemini remains the default Track 1 path and non-Google live calls are future |
| Cloud Run MVP hosting | Aligned | Official Cloud Run agent docs support this |
| Firestore canonical memory | Aligned | Good MVP persistence layer; complements ADK session concepts |
| Google Docs/Drive exports | Aligned | Clear tool actions for business output |
| MCP strategy | Mostly aligned | Need to keep tool boundaries clean and explicitly document MCP-compatible wrappers |
| Agents CLI | Needs stronger note | Should be checked before scaffolding |
| Agent Starter Pack | Needs correction | Treat as legacy/background due Agents CLI successor note |
| Agent Runtime | Aligned as stretch | Do not enable unless needed |
| RAG/Search | Aligned as future | Do not add to MVP unless scope changes |
| Budget | Aligned to user reality | Use <budget-guardrail> billing-account guardrail plus recommended <prototype-budget> project-only prototype budget |

## Blocked Or Screenshot-Needed Sources

| Source | Why Screenshot/Clip May Be Needed | User Action |
| --- | --- | --- |
| Google Cloud Console Agent Platform page | Project-specific and login-only | Send screenshots when checking project, model access, APIs, auth, or deploy state |
| Billing/Credits page | Project/account-specific | Send screenshot before cloud-heavy testing |
| Quotas page for Gemini/Vertex AI | Project/region-specific | Send screenshot if first model call fails or quota looks uncertain |
| Enabled APIs page | Project-specific | Send screenshot after enabling APIs |
| Service account/IAM page | Project-specific | Send screenshot after creating roles |
| Firestore setup page | Project-specific | Send screenshot after database creation |
| Cloud Run service page | Project-specific | Send screenshot only after local MVP passes and deployment begins |

## Current Recommendation Before Next Development Checkpoint

Do these in order:

1. Keep all public source links tracked in this file.
2. Keep manual ADK-compatible scaffold as the selected MVP path.
3. Use screenshots, not Obsidian clips, for Google Cloud Console verification.
4. Continue local development from the existing manual ADK-compatible scaffold.
