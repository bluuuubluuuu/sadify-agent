# SADify Decision Log

Date: 2026-05-02  
Status: Active reference
Last updated: 2026-06-19

## Purpose

This document records why major SADify product, architecture, cloud, testing, and demo decisions were made.

Use this file when:

- a decision feels unclear later
- a tool choice changes
- a demo or judging question needs explanation
- implementation work needs to know what is fixed, pending, or future
- another document seems to conflict with the current plan

## Traceability Sources

This decision log should be verified against:

- `CLAUDE.md`
- `context.md`
- `docs/superpowers/development/00_development_index.md`
- `docs/superpowers/development/01_product_scope.md`
- `docs/superpowers/development/02_agent_behavior_contract.md`
- `docs/superpowers/development/03_data_model_and_output_schema.md`
- `docs/superpowers/development/04_google_cloud_setup_runbook.md`
- `docs/superpowers/development/05_development_workflow.md`
- `docs/superpowers/development/06_demo_script_and_acceptance_checklist.md`
- `docs/superpowers/development/08_new_chat_handoff.md`
- `docs/superpowers/development/11_model_provider_linkage.md`
- `docs/superpowers/development/13_cloud_credit_consuming_services.md`
- `docs/superpowers/development/14_qna_workflow_refinement.md`
- `docs/superpowers/testing/test_cases/TC-028-evidence-based-readiness.md`
- `docs/superpowers/testing/test_cases/TC-026-mvp-drive-docs-save.md`
- `docs/superpowers/archive/development/consolidated-development.md`
- `docs/superpowers/archive/plans/consolidated-plans.md`
- `docs/superpowers/archive/specs/consolidated-specs.md`
- `docs/superpowers/archive/testing/test_cases/consolidated-test-cases.md`
- `docs/superpowers/diagrams/2026-04-29-sadify-architecture.md`
- `docs/superpowers/research/2026-05-02-track-1-resource-link-analysis.md`
- `docs/Google for Startups AI Agents Challenge.md`
- `docs/Google Cloud Hackathon (Req -_ SAD agent).md`

If a decision changes, update this log first, then update the affected source documents and tests.

## Decision Status Labels

| Status | Meaning |
| --- | --- |
| Confirmed | Current plan should follow this |
| Pending | Needs user confirmation, platform verification, or implementation evidence |
| Future | Useful later, not MVP |
| Avoid | Do not use unless the decision is reopened |
| Superseded | Older decision replaced by a newer one |

## Confirmed Decisions

| ID | Decision | Status | Why | Main Sources |
| --- | --- | --- | --- | --- |
| D-001 | Build for Track 1 | Confirmed | SADify is a net-new agent for a complex business problem | Track 1 source analysis, Devpost clipping |
| D-002 | Position SADify as an AI system analyst | Confirmed | The value is clarification and completeness, not generic document generation | Product scope, behavior contract |
| D-003 | Keep SADify cross-domain | Confirmed | The product should work for production/operations generally and not be locked to one demo domain | Product scope |
| D-004 | Keep demo scenario undecided for now | Confirmed | Agriculture/plantation inspiration is useful, but the best demo case should be chosen later | Product scope, demo checklist |
| D-005 | Support normal business files in MVP | Confirmed | Operations users commonly keep requirements in office files | Product scope, behavior contract |
| D-006 | Treat spreadsheets as MVP input | Confirmed | Spreadsheet files are common in industry workflows and can hold operational requirements | Product scope, file extraction test |
| D-007 | Treat image input as first priority potential development | Future | Useful for field/site contexts, but file extraction MVP comes first | Product scope |
| D-008 | Use guided but flexible completeness behavior | Confirmed | SADify should guide clarification but still allow draft generation with assumptions | Product scope, behavior contract |
| D-009 | Separate completeness and confidence | Confirmed | Completeness measures missing info; confidence measures interpretation reliability | Behavior contract, tests |
| D-010 | Separate problem severity from recommendation priority | Confirmed | Missing info and suggested features serve different purposes | Behavior contract |
| D-011 | Use consistent labels and visual formats | Confirmed | Users need easy tracking of risks, assumptions, sources, and recommendations | Behavior contract |
| D-012 | Use canonical structured JSON as source of truth | Confirmed | Structured data is easier to validate, render, version, and export | Data model schema |
| D-013 | Store canonical project data in Firestore | Confirmed | Firestore is simpler and lower overhead than relational infrastructure for this MVP | Data model schema, runbook |
| D-014 | Generate Obsidian-compatible wiki Markdown | Confirmed | Wiki notes make requirements chunked, connected, and readable by humans and coding tools | Data model schema, architecture |
| D-015 | Store wiki files in Google Drive project folders | Confirmed | Drive keeps generated docs accessible and shareable without extra storage complexity | Data model schema, runbook |
| D-016 | Use project-level SAD, not one SAD per requirement | Confirmed | One requirement is often too small for a full SAD; requirements become cards/wiki notes | Data model schema |
| D-017 | Use one graph-style `knowledge_items` collection | Confirmed | Unified nodes make requirement, entity, workflow, decision, actor, report, and source linking simpler | Data model schema |
| D-018 | Use clear stable IDs and readable slugs | Confirmed | Human users and coding tools both need understandable references | Data model schema |
| D-019 | Require wiki verification before overwrite | Confirmed | Overwriting verified wiki notes is risky without checks and owner approval | Data model schema, workflow |
| D-020 | Include human verification for wiki changes in MVP | Confirmed | Owner approval prevents unsafe automated promotion of wiki drafts | Data model schema, tests |
| D-021 | Use Google ADK as the agent framework | Confirmed | ADK aligns with Track 1 and official Google agent resources | Source analysis, runbook |
| D-022 | Use Vertex AI Gemini for model calls | Confirmed | Best fit for Google Cloud challenge alignment and ADK integration | Source analysis, runbook |
| D-023 | Use `gemini-2.5-flash` first | Confirmed | Cost-conscious, stable, and suitable for MVP iteration | Source analysis, runbook |
| D-024 | Do not switch to Gemini preview models automatically | Confirmed | Preview models need stability, pricing, region, and ADK compatibility checks first | Source analysis |
| D-025 | Check Agents CLI before scaffolding | Superseded | Agents CLI was checked during readiness; manual ADK-compatible scaffold was selected in D-048 | Source analysis, workflow |
| D-026 | Treat Agent Starter Pack as background only | Confirmed | Public repo points future development to Agents CLI | Source analysis |
| D-027 | Build local first, deploy to Cloud Run after local checkpoints pass | Confirmed | Reduces demo risk and protects credits | Workflow, runbook |
| D-028 | Use one Cloud Run service for MVP deployment | Superseded | This applied to the Streamlit prototype. The proper MVP uses two Cloud Run services per D-058 | Runbook, architecture, MVP web app design spec |
| D-029 | Keep Agent Runtime / Agent Engine as stretch | Confirmed | Managed runtime adds setup and cost complexity not required for MVP | Source analysis, runbook |
| D-030 | Keep tool boundaries MCP-compatible | Confirmed | Track 1 emphasizes MCP/tool integration, but remote MCP server can wait | Source analysis, behavior contract |
| D-031 | Do not add RAG/Vertex AI Search to MVP | Confirmed | Uploaded files, canonical JSON, Firestore, and wiki memory are enough for prototype | Source analysis |
| D-032 | Use Google Docs, PDF, DOCX, and wiki Markdown as normal outputs | Confirmed | Users need practical business formats and Obsidian-compatible knowledge files | Product scope, behavior contract |
| D-033 | Keep GitHub Issues export as stretch | Confirmed | Useful and agentic, but adds auth/API risk after core exports | Product scope |
| D-034 | Use `sadify-agent-sa` runtime service account | Confirmed | Keeps runtime access explicit and easier to audit | Runbook |
| D-035 | Share Drive folder with service account instead of using IAM for Docs/Drive | Superseded for MVP | This was valid for the Streamlit prototype path. The proper MVP uses user-owned Drive/Docs files through OAuth and backend grant storage | Runbook, MVP web app design spec |
| D-036 | Keep project region as `asia-southeast1` | Confirmed | Good APAC/Malaysia latency and matches current plan | Runbook |
| D-037 | Track real budget context from the user's Google Cloud billing setup | Confirmed | The current confirmed guardrail is an overall <budget-guardrail> billing-account budget with actual-spend alerts; do not rely on guide credit amounts as the project budget | Runbook, readiness checklist |
| D-038 | Prefer a small prototype budget alert around <prototype-budget> before heavy cloud usage | Confirmed | Early warning protects the development credit; the current larger <budget-guardrail> billing-account budget is acceptable for setup but warns later than ideal | Runbook, readiness checklist |
| D-039 | Avoid GKE, VMs, BigQuery, Cloud SQL, Dataflow, Pub/Sub, GPUs, and similar heavy services for MVP | Confirmed | They add unnecessary cost/complexity for prototype | Runbook |
| D-040 | Use safe engineered development checkpoints | Confirmed | Functional features need tests, expected output, real output, and evidence | Workflow, test index |
| D-041 | Build diagnostics early | Confirmed | DevTools, logs, debugging, and HTTP response issues should be visible before cloud deployment | Workflow, TC-011 |
| D-042 | Keep UI polish flexible until core behavior works | Confirmed | Functional correctness is more important than visual polish early | Workflow |
| D-043 | Keep trustworthy core features free/basic | Confirmed | Project history, version history, exports, completeness, and clarifications are core usefulness, not artificial premium locks | Product scope |
| D-044 | Premium features should scale with usage, collaboration, customization, and enterprise needs | Confirmed | Revenue should follow real user dependency and workload, not blocking essential value | Product scope |
| D-045 | Use screenshots for Google Cloud Console verification | Confirmed | Console pages are login/project-specific and not reliable public sources | Source analysis |
| D-046 | Treat handoff and readiness docs as required pre-development references | Confirmed | The project must stay easy to resume in new chats/tools without losing context | New chat handoff, readiness checklist |
| D-047 | Keep root `CLAUDE.md` and `context.md` as top-level agent references | Confirmed | Coding agents need a fast root-level map for behavior, quality rules, architecture, dataflow, and source lookup | Root files, development index |
| D-048 | Use manual ADK-compatible scaffold for MVP development | Confirmed | `agents-cli` and local `gcloud` are not installed, and manual scaffolding is easier to debug while preserving `root_agent` compatibility | Readiness checklist, user confirmation |
| D-049 | Use Python 3.13, `.venv`, and `pip` for local development | Confirmed | The local environment verified `google-adk`, `adk`, Streamlit, pytest, and file extraction dependencies inside `.venv` | Readiness checklist, shell verification |
| D-050 | Keep `.env` local and ignored; commit `.env.example` only | Confirmed | The Drive folder ID is configuration, not source; `.env.example` documents needed keys without secrets | Readiness checklist, `.gitignore` |
| D-051 | Treat Google Cloud setup as ready for careful cloud-connected development | Confirmed | APIs, service account, IAM roles, Firestore Native Mode, and Drive folder sharing were verified | Readiness checklist, Cloud Shell, console screenshot |
| D-052 | Keep Google/Gemini as the default model route while adding provider-neutral model routing | Confirmed | This preserves Track 1 alignment and allows separate models for requirement analysis, final SAD generation, and fallback without forcing provider lock-in | Model provider linkage, repo commit `0ce2b68` |
| D-053 | Keep live non-Google provider adapters out of the current prototype until requirement analysis is implemented | Confirmed | Provider calls should be tested against real SADify tasks; adding disconnected LLM calls now would increase secrets, cost, and debugging risk | Model provider linkage |
| D-054 | Use business-first language in requester-facing UI | Confirmed | The primary user is a production/business requester, so the UI should ask practical questions while internal services keep technical categories for SAD generation | Behavior contract, Checkpoint 3 UI tests |
| D-055 | Treat the deployed deterministic Cloud Run app as the basic prototype baseline | Confirmed | User wants to start improvements after C15; the deployed app loads and proves the core requirement-analysis experience, while live Gemini, Firestore, Drive/Docs, and log-admin checks become improvement backlog instead of blocking the baseline | TC-012, C14/C15 plan, Playwright smoke |
| D-056 | Move from Streamlit prototype to proper web-app MVP | Confirmed | The prototype is functional proof only; the MVP needs a real product foundation for auth, project workspace, Drive Picker, and user-friendly Q&A | MVP web app design spec |
| D-057 | Use Next.js/React frontend plus Python FastAPI backend | Confirmed | This gives a proper UI/auth/Drive experience while preserving reusable Python services and tests | MVP web app design spec |
| D-058 | Deploy the MVP as two Cloud Run services | Confirmed | Separate frontend and backend services are more complete and easier to debug than bundling the product into one service | MVP web app design spec |
| D-059 | Use Firebase Auth / Google Identity Platform for sign-in | Confirmed | The MVP needs persistent Google sign-in, guest upgrade, and user identity without custom auth risk | MVP web app design spec |
| D-060 | Keep Firestore access backend-only | Confirmed | Backend-only writes protect canonical schema validation, auditability, and security boundaries | MVP web app design spec |
| D-061 | Persist guest drafts in Firestore and migrate safely after sign-in | Confirmed | Guest users can validate ideas without losing work; safer audit migration keeps the original guest draft intact | MVP web app design spec |
| D-062 | Use user-owned Drive/Docs files through OAuth | Confirmed | Real users should own generated SAD/wiki/source files in their selected Drive project repo | MVP web app design spec |
| D-063 | Store OAuth grants through a backend-mediated token store and provide Disconnect Google Drive | Confirmed | Stored grants allow later Drive updates, but users must be able to revoke the connection | MVP web app design spec |
| D-064 | Ask Drive/Docs permission only when connecting a project repo | Confirmed | Initial sign-in remains lighter, while Drive/Docs scopes are requested only when needed | MVP web app design spec |
| D-065 | Use live Gemini structured JSON for MVP reasoning | Confirmed | The MVP must prove an AI analyst workflow, not only deterministic rules; strict schemas keep output safe | MVP web app design spec |
| D-066 | Keep model switching as future priority 1 but do not expose a model picker in the first MVP | Confirmed | Gemini is required first for Track 1, while backend interfaces should remain replaceable later | MVP web app design spec, model provider linkage |
| D-067 | Use one-question-at-a-time Q&A with choices, amend field, stable question-area status, and one overall readiness score | Confirmed | Users should not need to understand SAD methodology; SADify should ask simple business questions and show only useful progress | Stable questionnaire plan design |
| D-073 | Use a stable questionnaire plan with fixed core categories, reviewed extras, frozen order, and slot-based completion | Confirmed | Manual testing showed that turn-by-turn Gemini category reconstruction creates drift and breaks trust | Stable questionnaire plan design |
| D-074 | Backend owns active category, active slot, and readiness; Gemini phrases questions inside that locked target | Confirmed | Prompt-only control is insufficient; the workflow must be enforced in code | Stable questionnaire plan design |
| D-075 | At `100%` required readiness, show a `Ready to draft` handoff with optional refinements separated and collapsed | Confirmed | Required work should feel complete; optional detail gathering must not look like a blocker | Q&A ready-state design |
| D-076 | Move understanding summary, saved answers, and completed areas behind expanders in the normal Q&A view | Confirmed | The user should focus on the current answer step without losing traceability | Q&A ready-state design |
| D-077 | Include saved questionnaire answers in SAD preview context | Confirmed | User-confirmed answers are requirement facts and must survive the handoff into document generation | Q&A ready-state design |
| D-078 | Merge original request facts and user-confirmed answers into one authoritative SAD synthesis input before generation | Confirmed | The live clinic smoke proved that merely appending answers is insufficient; the preview must reason over one coherent facts view | 2026-05-18 clinic manual smoke, Q&A workflow note |
| D-079 | Keep internal fallback/retry diagnostics out of business-facing SAD assumptions | Confirmed | Diagnostics help developers, but they degrade user trust when shown as requirement assumptions | 2026-05-18 clinic manual smoke |
| D-080 | Treat readiness coherence as a progression gate before wiki work | Confirmed | A `100%` Q&A screen followed by a `35%` SAD preview is contradictory and not acceptable for MVP progression | 2026-05-18 clinic manual smoke |
| D-081 | Keep both draft-ready and IT-ready layers inside the MVP, implemented sequentially | Confirmed | The first layer gives early value, while the second layer is still required before the MVP is truly complete | User clarification on 2026-05-18 |
| D-082 | Keep the base business request clean and separate from Q&A transport history | Confirmed | The 2026-05-19 video smoke showed appended `Previous question` and `Previous answer` logs leaking into the displayed SAD business request | TC-021V, data model schema, Q&A workflow note |
| D-083 | Local fallback SAD output must be structured and synthesized, not a raw diagnostic dump | Confirmed | A transport-safe fallback is not enough; users need a readable first SAD draft that interprets confirmed answers and amendments | TC-021V, SAD synthesis quality spec |
| D-084 | The normal SAD preview must be business-facing even when local fallback is used | Confirmed | The 2026-05-19 TC-021V manual smoke showed that clean transport is not enough; users should not see fallback/debug labels, contradictory readiness, repeated request text, or informal amendment wording in the main SAD draft | TC-021W, SAD synthesis quality spec |
| D-085 | Treat evidence-first Q&A depth as the next SAD quality gate before wiki work | Confirmed | The 2026-05-20 workshop smoke showed broad preset questions and answer labels can make Q&A look complete without enough detailed workflow, rule, exception, access, integration, and non-functional evidence | TC-021X, evidence-first Q&A design |
| D-086 | Apply user-facing preview coherence rules to valid Gemini previews, not only fallback previews | Confirmed | TC-021W improved fallback presentation, but a valid preview still showed `60% Low confidence` and visible IT readiness after Q&A reached `100%` | TC-021X, workshop manual smoke |
| D-087 | Treat TC-021X as a local improvement, not the final Phase 4 pass | Confirmed | TC-021X improved the workshop path locally, but manual workshop/tuition smoke still showed generic Q&A, narrow domain hardcoding, fallback wording leakage, internal slot source refs, and invented generic rules | TC-021Y, 2026-05-21 tuition smoke |
| D-088 | Make domain-aware evidence and clean SAD output the next gate before wiki work | Confirmed | The next fix must generalize beyond workshop/clinic branches: extract request facts, ask missing-facet questions, preserve fact-bearing choices, clear stale preview state, and hide fallback/debug/source-ID internals from user-facing SAD output | TC-021Y design, Q&A workflow note |
| D-089 | Use AI-judged, quote-validated per-slot evidence for draft readiness | Confirmed | Keyword/phrase readiness tables caused brittle domain patches and arbitrary scores; Gemini may judge each required slot, but the backend validates quoted evidence against the actual request/source material, downgrades ungrounded verdicts, aggregates readiness deterministically, and derives confidence | Evidence-based readiness design, TC-028 |
| D-068 | Use fixed core wiki taxonomy with approved project-specific folder/file proposals | Confirmed | SADify should prevent wiki drift while still allowing Gemini to propose new knowledge structures when needed | MVP web app design spec |
| D-069 | Treat Wiki as the living project brain and SAD as formal versioned output | Confirmed | The wiki should stay current after validation and approval, while SAD versions preserve formal history | MVP web app design spec |
| D-070 | First MVP save path is SAD Google Doc, wiki Markdown files, and source files | Confirmed | This proves the linked project repo; PDF/DOCX return after the core Drive/Docs path is stable | MVP web app design spec |
| D-071 | Start MVP implementation with a thin full-stack slice | Confirmed | Next.js -> FastAPI -> guest Firestore draft -> live Gemini analysis proves the riskiest integration path early | MVP web app design spec |
| D-072 | Execute the MVP in the isolated `mvp-monorepo-scaffold` worktree checkpoint by checkpoint | Confirmed | Keeps the MVP migration separate from the Streamlit prototype and preserves the user's stop/review rhythm | MVP implementation plan, TC-016 to TC-019 |
| D-090 | Persist Project/SAD-save/wiki-state/Drive-grant repositories to Firestore Native Mode behind `SADIFY_PERSISTENCE=firestore` (default `memory`); keep analysis/Q&A and source uploads in-memory | Confirmed | In-memory repositories lose all data on Cloud Run cold starts, across instances, and on redeploy, so deployed save history/projects would be unreliable; Firestore is the documented canonical store. Analysis/Q&A is an ephemeral working session that should reset. Each repo is a clean seam, so the swap is contained and default `memory` keeps offline tests/dev byte-identical | TC-030, CLAUDE.md, 04_google_cloud_setup_runbook.md |
| D-091 | Run all Firestore transactions through the official `firestore.transactional` decorator (`run_in_transaction` helper), allocating ID counters in their own transactions before the main write | Confirmed | A manual un-begun `client.transaction()` raises `Transaction not in progress` on the first transactional read against real Firestore, and interleaved counter read/writes violate read-before-write. Both P0s passed mocked tests but failed live; the decorator performs `_begin`/`_commit`/retry correctly | TC-030 (commit 21616c7), dual Claude+Codex review |
| D-092 | Replace the stacked debug-panel frontend with a guided adaptive 3-pane chat workspace (Sidebar \| Chat \| Preview), changing only `apps/web` and the Python static UI tests; no backend or `lib/api.ts` shape changes | Confirmed | The debug-panel UI was user-facing but built for diagnostics. The redesign recomposes the ~13 panels into a stage-driven shell whose logic lives in extracted hooks that hold the prior request/transport/fallback code verbatim (Q&A carry-forward string byte-identical), so everything tested previously behaves the same. CSS Modules + central design tokens + inline Phosphor SVG icons (no new dependency). Shipped commits 05fb247..56f647d plus Codex follow-up de7209f (persistent wiki-updated indicator, per-project repo link, scrollbar polish) | UI redesign spec + plan (2026-05-31), branch `codex/mvp-monorepo-scaffold` |
| D-092a | The redesigned readiness pane must bind coverage and the readiness label/confidence to the stable `questionnaire` state (`questionnaire.categories`, `questionnaire.draft_readiness`), falling back to raw `analysis.categories`/`analysis.readiness` only when `questionnaire` is null | Confirmed | The redesign regressed the binding to the raw per-turn Gemini/fallback fields: raw categories are unratcheted (coverage rows flicker/disappear) and raw readiness is "Fallback question ready"/Low even at 92-100%. The backend already exposes ratcheted, stable data in `questionnaire.*`. Frontend-only fix, commit 87d059d | TC-031, decision D-092, commit 87d059d |
| D-093 | Readiness score (completeness %) and readiness confidence (evidence-grounding quality) are independent by design; keep the mechanism and reframe the confidence badge as evidence quality in the UI rather than changing the formula | Confirmed | Score weights `not_applicable`/`strong`=1.0, `partial`=0.5; confidence needs ≥70% applicable `strong` and is forced Low by ≥2 this-turn quote downgrades or `none > half`. So 90%+/"Ready for draft" with Low confidence is expected, not a bug. The "Low confidence" badge next to "Ready for draft" only reads as contradictory because of wording. Any change to the this-turn-vs-merged `downgrade_count` coupling is a benchmarking decision, deferred | TC-031, `slot_evidence.py::derive_confidence`, `questionnaire_plan.py`, dual Claude+Codex verification |
| D-094 | Deploy TC-027 as two Cloud Run services via `gcloud run deploy --source` (Cloud Build from per-service Dockerfiles), full live stack (`SADIFY_DRIVE_MODE=live` + `SADIFY_PERSISTENCE=firestore`), `min-instances=0`, runtime identity `sadify-agent-sa` (ADC) | Confirmed | Source-based deploy has the fewest moving parts for an MVP demo (no manual Artifact Registry/CI). Scale-to-zero avoids idle cost. Frontend `NEXT_PUBLIC_*` are build-time baked, so backend deploys first, then frontend builds with the backend URL, then backend CORS + OAuth/Firebase origins update to the frontend URL. Execution gated on billing confirmation + IAM checklist + explicit go-ahead | TC-027 plan (2026-06-02), runbook, user decision |
| D-095 | TC-027 two-service Cloud Run deploy PASSED in production; MVP complete | Confirmed | Backend image needs both `services/api/src` and root `src/` so the backend Dockerfile lives at the worktree root and deploys with `--source .`; `services/api/pyproject.toml` was missing three runtime deps (`python-multipart`, `firebase-admin`, `google-genai`) that the local .venv masked — fixed in commit 58aa315. Frontend `NEXT_PUBLIC_*` baked via `apps/web/cloudbuild.yaml`. Two console steps (Firebase Authorized domains + OAuth JS origins for the run.app frontend) are required post-deploy and were the cause of the only mid-smoke failures. Cloud Run deterministic URL format `<service>-<projectNumber>.<region>.run.app` let CORS be pre-baked. Optional `sadify.web.app` via Firebase Hosting deferred | TC-027 (PASS 2026-06-03), commits 18e9adb/fee9169/58aa315 |
| D-096 | Expose Gemini model choice as a runtime picker backed by a backend-owned allowlist | Confirmed | Resolves P-009 without turning model choice into deploy-time config or enabling non-Google adapters. The shipped Gemini catalog is Flash default, Pro, and Flash-Lite. Pro needs model-aware generation config because it rejects `thinking_budget=0`; Flash/Flash-Lite preserve the previous thinking-disabled config. Missing, invalid, or allowlisted-but-unavailable selected IDs fall back to backend default; live non-Google providers remain deferred under P-017. TC-032 passed production smoke on 2026-06-04 after deploy to `sadify-api-00005-pc2` and `sadify-web-00002-vzw` | TC-032 implementation + production smoke, ae97f8e, e44951c, Vertex model probe |
| D-097 | Make `/agent/approve` deterministic and keep the LLM out of approved write execution | Confirmed | A live GATE 3 test showed the original approval route re-entered the agent loop, regenerated a new preview, and consumed the token without saving the approved preview. The safety gate still held, but approve-to-save reliability was wrong. `/agent/approve` now executes only the approved actions, does not re-run the LLM, consumes the token on success, keeps it on hard write failure, and turns wiki conflict into re-approval | TC-034, 639d043, 686e3de, CC live GATE 3 probe |
| D-098 | Add the TC-034 agent activity timeline additively via POST stream + frontend overlay | Confirmed | P4 makes the agent visible without changing the manual flow. `POST /agent/finalize/stream` returns NDJSON consumed with `fetch()` + `ReadableStream` so Firebase Authorization stays in headers; the `AgentTimeline` overlay renders reasoning, tool steps, and approval prompts while preserving manual save/wiki actions | TC-034, d1285d2, 31d256d, tests/test_tc034_agent_timeline_ui.py |
| D-099 | Let the finalize agent collaborate with the completed Q&A instead of re-asking answered gaps | Confirmed | The Q&A engine is the trusted human fact-source. When a valid draft exists, a stray `ask_clarification` must not override the draft; review `tighten`/`ask` issues fold into the SAD's assumptions/open questions, and `asked_clarification` is reserved for blocked basics when no draft can be produced | TC-034, e0f9fd1 |
| D-100 | Close the TC-034 review -> revise loop with grounded feedback and deterministic convergence guards | Confirmed | `review_sad` issues are fed into the next regeneration with the prior draft and a no-fabrication instruction, but regeneration is allowed only after the current draft receives a `regenerate` verdict and the verdict is consumed once. The same checkpoint added a deterministic draft safety-net for weak model stops, lazy live Drive/Secret resolution in the agent wiki path, single agent entry UX, and wiki-conflict completed-save surfacing so overwrite re-approval keeps user trust | TC-034, 0889aab, 18a6aa9, bce7488, da153be |
| D-101 | Use GitHub Issues via MCP as the Track-1 external action | Confirmed | GitHub issue creation demonstrates an agentic external tool boundary without replacing the existing Drive/Docs path. It remains approval-gated and uses a user-supplied PAT held only in memory | TC-034 P5 GitHub Issues MCP plan, TC-036 |
| D-102 | Persist immutable GitHub issue sets and deduplicate sequential retries by stable body marker | Confirmed | A prepared set is owned by `(grant_id, project_id, save_id)` and locks its first repository. Relaunch creates a fresh GATE 3 approval without rerunning extraction. Matching markers across paginated open/closed issues are skipped; title matching is intentionally rejected because titles can change or collide. The concurrent read-before-write race is accepted for v1 and is not described as exactly-once | TC-036, GitHub issue relaunch design, commits 074f17b..1d3fee2 |

## Pending Decisions

| ID | Decision Needed | Status | Why It Matters | Current Default | Needed Before |
| --- | --- | --- | --- | --- | --- |
| P-001 | Agents CLI scaffold vs manual ADK-compatible scaffold | Superseded by D-048 | Determines initial project structure and tool workflow | Manual ADK-compatible scaffold selected | Done before local project scaffold |
| P-002 | Exact first demo scenario | Pending | Demo should best show messy input, missing info, business rules, and developer output | Keep agriculture/plantation inspiration but do not lock yet | Demo recording |
| P-003 | Whether live requirement analysis uses pure ADK immediately or a thin model-router adapter first | Confirmed | Affects coding speed, provider routing, and ADK compatibility checks | Use backend model-routing interfaces with Gemini first; keep ADK-compatible core available | MVP web app design spec |
| P-004 | Exact Google Drive root folder ID | Confirmed | Exports need the folder ID for placement | Saved in local `.env`; not printed in docs or git | Export integration |
| P-005 | Whether billing credit is attached and budget alert is active | Confirmed | Cloud usage should not proceed without credit safety | <budget-guardrail> billing-account budget exists with actual-spend alerts; smaller project-only budget still recommended before heavy loops | Cloud-heavy testing |
| P-006 | Whether required APIs are enabled | Confirmed | Model calls, Firestore, Drive/Docs, and Cloud Run depend on APIs | Required API enable command completed successfully | Cloud setup |
| P-007 | Whether Firestore database exists in `asia-southeast1` | Confirmed | Persistence depends on the correct database location | `(default)` Firestore Native database created in `asia-southeast1` | Persistence checkpoint |
| P-008 | Whether service account roles are correctly assigned | Confirmed | Runtime identity needs least-privilege access | Vertex AI User, Cloud Datastore User, Secret Manager Secret Accessor granted | Cloud Run deployment |
| P-009 | Whether `gemini-2.5-pro` is needed for final SAD generation | Confirmed by D-096 | Pro may improve quality but costs more, so the user chooses at runtime | Runtime picker defaults to Flash | TC-032 implementation |
| P-010 | Exact free/premium file size and output size limits | Pending | Pricing and plan limits should be user-dependent and fair | Decide later after MVP measurements | Productization |
| P-011 | Image input limit and pricing position | Pending | Image support may be important for field work but can increase cost | Future, possibly limited | Post-MVP scope |
| P-012 | Whether GitHub Issues export is included in demo | Pending | It adds agentic action but increases auth risk | Stretch only | Demo finalization |
| P-013 | Whether generated diagrams are included in MVP | Pending | Diagram output is useful but may distract from SAD/wiki core | Textual DFD-style description first | SAD renderer |
| P-014 | Whether Obsidian local vault sync is manual or automated | Pending | MVP only needs generated Markdown in Drive; local vault use may be manual | Manual/open later | Wiki demo |
| P-015 | Exact retention/version limits for free vs paid plans | Pending | Version history is core, but storage scale can be priced | Keep version history in core MVP | Pricing design |
| P-016 | Whether Agent Runtime is used in final submission | Pending | Could impress if stable, but may add setup complexity | Cloud Run first | Final cloud deployment strategy |
| P-017 | Exact non-Google providers and models to enable for live calls | Pending | External models add secrets, SDKs, cost, and quality comparison work | Keep only route metadata and readiness checks for now | After requirement-analysis flow works |
| P-018 | Exact Google OAuth scopes for Drive Picker, Drive writes, and Docs creation | Partly confirmed | Scopes affect user trust, security review, and save/export reliability | TC-023 preflight chose Google Identity Services authorization code flow and `drive.file` first; Docs scope remains deferred to the save checkpoint | OAuth implementation plan |
| P-019 | Exact least-privilege Secret Manager roles for backend OAuth token storage | Pending | Current service account role may be insufficient for creating/updating token secrets | Verify official IAM roles before implementation | OAuth implementation plan |
| P-020 | Firebase web config and OAuth redirect setup for local sign-in | Confirmed | TC-019 needed live Google sign-in and backend real ID-token verification before guest draft migration | Firebase web config and local Firebase Admin credential are configured outside git | Done for local TC-019; deployed Cloud Run auth config remains later |

## Future Decisions

| ID | Future Area | Status | Notes |
| --- | --- | --- | --- |
| F-001 | Multi-user collaboration | Future | Potential premium/team feature after solo MVP |
| F-002 | Approval workflow with production, IT, and manager roles | Future | MVP owner approval exists for wiki verification only |
| F-003 | Full project management system | Future | Could become premium, but not needed for proof of SADify core |
| F-004 | Advanced diagram editor | Future | Useful for DFD/ERD/workflow refinement |
| F-005 | Voice input | Future | Useful for field/on-site users |
| F-006 | Advanced domain templates | Future | Potential paid industry packs after generic core is proven |
| F-007 | RAG Engine / Vertex AI Search | Future | Add only if file/wiki memory becomes insufficient |
| F-008 | Source extraction snapshots | Future | Important for deeper auditability and smarter compacted project memory |
| F-009 | A2A / marketplace readiness | Future | Track 3-style direction, not Track 1 MVP |
| F-010 | Enterprise controls | Future | SSO, audit logs, admin controls, custom standards |

## Avoid Decisions

| ID | Avoided Choice | Status | Why |
| --- | --- | --- | --- |
| A-001 | Building on GKE for MVP | Avoid | Overkill for prototype and higher cost risk |
| A-002 | Using Compute Engine VM for MVP | Avoid | More operations work than Cloud Run |
| A-003 | Using Cloud SQL as first database | Avoid | Relational schema overhead is not needed for flexible messy requirements |
| A-004 | Using BigQuery for MVP storage | Avoid | Analytics warehouse is not needed for prototype requirement memory |
| A-005 | Adding RAG infrastructure before local file/wiki flow works | Avoid | Adds cost and complexity before need is proven |
| A-006 | Locking the product to agriculture/plantation only | Avoid | Demo can be inspired by agriculture, but product should stay generic |
| A-007 | Making core trust features premium-only | Avoid | Completeness, history, basic exports, and versioning are central user value |
| A-008 | Deploying to Cloud Run before local MVP passes | Avoid | Increases cost and debugging risk |

## Decision Update Rules

Before changing a confirmed decision:

1. Add a short note under `Change Notes`.
2. Update the decision status if needed.
3. Update affected source docs listed in `Traceability Sources`.
4. Update matching tests if behavior changes.
5. If a Google Cloud service/tool changes, update `04_google_cloud_setup_runbook.md`.
6. If scope changes, update `01_product_scope.md`.
7. If agent behavior changes, update `02_agent_behavior_contract.md`.
8. If storage/output changes, update `03_data_model_and_output_schema.md`.
9. If checkpoint order changes, update `05_development_workflow.md` and `testing/test_case_index.md`.

## Change Notes

| Date | Change | Reason | Affected Docs |
| --- | --- | --- | --- |
| 2026-05-02 | Created decision log with confirmed, pending, future, and avoid decisions | User requested all decisions documented | Development index, README |
| 2026-05-02 | Added handoff/readiness docs as required pre-development references | User wants every new chat/tool to have enough context to continue safely | Decision log, development index, README, handoff, readiness checklist |
| 2026-05-02 | Added root `CLAUDE.md` and `context.md` references | User requested top-level agent guidance for coding behavior and functional context | Root files, development index, README, handoff, readiness checklist |
| 2026-05-02 | Recorded pre-development checkpoint: manual scaffold, local environment, cloud setup, Firestore, Drive folder, and budget caveat | User completed Q1-Q6 checks before development | Decision log, readiness checklist, handoff, context |
| 2026-05-04 | Recorded implementation start and model-routing architecture refinement | Local scaffold, diagnostics, and provider-neutral route metadata now exist; docs needed alignment before the next checkpoint | Root files, README, index, workflow, runbook, architecture, handoff, test index |
| 2026-05-11 | Recorded basic deployed prototype baseline after Cloud Run smoke | User wants to treat this as the baseline before improvements; deployed health and deterministic requirement analysis passed, with live cloud integrations deferred | TC-012, test index, C14/C15 plan, handoff |
| 2026-05-11 | Recorded prototype-to-MVP architecture shift | User selected proper web app MVP with Next.js, FastAPI, Firebase Auth, live Gemini, backend-only Firestore, user-owned Drive/Docs OAuth, and checkpoint gates | MVP design spec, development index, workflow, test index |
| 2026-05-12 | Recorded MVP implementation stop point after MVP-04 local auth foundation | MVP-00 through MVP-03 passed; TC-019 is blocked for full live pass until Firebase web config/OAuth setup is provided; user asked to stop and keep docs/dev notes updated | Handoff, development index, MVP test plan, runbook, test index, TC-019 |
| 2026-05-13 | Marked TC-019 passed after live local Firebase Auth verification | User completed Google sign-in; backend `/auth/session` returned 200 OK and UI showed the signed-in persistent session message | TC-019, test index, handoff, development index, workflow, root context |
| 2026-05-13 | Marked TC-020 passed for local fake-store guest draft migration | Guest drafts can be created, copied to a signed-in project record, and kept for audit without destructive migration; real Firestore cloud persistence remains deferred | TC-020, test index, handoff, development index, workflow, root context |
| 2026-05-14 | Marked TC-023 passed for local Drive repo OAuth contract | Backend-mediated repo grant routes, `drive.file` scope intent, config-aware OAuth-code UI, planned project repo folders, and disconnect save blocking are verified locally; live token exchange, Secret Manager storage, Drive writes, and Picker remain deferred | TC-023, test index, MVP test plan, handoff, development index, workflow, root context |
| 2026-05-14 | Marked TC-024 passed for local SAD preview and IT readiness | Structured SAD preview schema, blocking-basics gate, IT readiness checklist, assumptions/open questions, source refs, change tracking, and temporary preview UI are verified locally; live Gemini preview smoke and Drive/Docs save remain deferred | TC-024, test index, MVP test plan, handoff, development index, workflow, root context |
| 2026-05-18 | Added ready-state handoff decisions after the manual `100%` Q&A rerun | The continuity refactor now reaches completion, but the completion screen is noisy and SAD preview currently drops saved Q&A answers from its prompt context | Ready-state design spec, Q&A workflow note, development index, workflow, test index |
| 2026-05-18 | Added SAD synthesis quality decisions after live preview smoke | The preview route now returns `200`, but the document still conflicts with Q&A readiness, under-credits known facts, leaks fallback diagnostics, and mixes in weakly grounded generic content | Q&A workflow note, development index, handoff, MVP test plan, test index, TC-021T |
| 2026-05-18 | Confirmed two readiness layers remain within MVP scope | User clarified that draft-ready comes first for build order, but IT-ready refinement is still part of the MVP definition | Product scope, behavior contract, data model, decision log |
| 2026-05-19 | Added TC-021V fallback SAD composition decisions | Manual video smoke proved TC-021U route safety but showed the fallback SAD still leaks Q&A transport logs and does not yet synthesize amendments into proper SAD sections | SAD synthesis quality spec, Q&A workflow note, data model, TC-021U, TC-021V |
| 2026-05-19 | Added TC-021W user-facing SAD draft quality decision | TC-021V manual smoke partially passed transport cleanup but still failed the actual SAD draft quality bar due to debug framing, repeated request text, shallow answer rendering, literal amendment wording, and conflicting readiness labels | SAD synthesis quality spec, Q&A workflow note, TC-021V, TC-021W |
| 2026-05-20 | Added TC-021X evidence-first Q&A and valid preview coherence decisions | TC-021W automated checks passed, but workshop manual smoke failed progression because Q&A remained too generic and valid preview presentation still contradicted draft readiness | CURRENT, development index, workflow, Q&A note, test index, MVP test plan, TC-021W, TC-021X |
| 2026-05-21 | Added TC-021Y domain-aware Q&A and SAD quality hardening decisions | TC-021X local checks improved the workshop path, but manual tuition smoke proved the approach was too narrow and still leaked fallback/source-ID/generic rule issues | CURRENT, development index, workflow, Q&A note, test index, MVP test plan, TC-021X, TC-021Y |
| 2026-05-23 | Amended readiness decision for TC-028 evidence-based readiness | Keyword/phrase readiness patching is superseded; readiness is now based on AI per-slot evidence verdicts that quote actual material, with backend quote validation, deterministic aggregation, `not_applicable` handling, and derived confidence | Evidence-based readiness spec, plan, Q&A workflow note, data model, TC-028 |
| 2026-05-25 | Split TC-026 into local-first save contract and future live Drive/Docs slice | The local/fake save path proves product behavior and idempotency without cloud writes; live OAuth/Drive/Docs/Secret Manager work remains future TC-026B after explicit approval | TC-026, CURRENT, test index |
| 2026-05-25 | TC-026B live Drive/Docs save shipped behind double env gate `SADIFY_DRIVE_MODE=live` + `SADIFY_TC026B_LIVE=1` | Real OAuth code exchange, real `SADify Projects` Drive folder, real Markdown-to-Doc upload, refresh token in Secret Manager (`sadify-drive-token-<uid>`), disconnect deletes per-user secret. Local mode stays the default so 332-test regression and TC-026 manual smoke remain offline. | TC-026B, CURRENT, test index, runbook |
| 2026-05-25 | schemas.py `DriveRepoRecord.token_store` Literal gains `"secret_manager"` value (append-only) | Required so live-mode connect can produce a `DriveRepoRecord` with `token_store="secret_manager"`. Existing `"secret_manager_pending"` preserved for the intermediate failure state. Surgical, justified, append-only edit. | schemas.py, TC-026B plan |
| 2026-05-27 | Split TC-025 into TC-025A snapshot (shipped) and TC-025B encyclopedia (next slice) | TC-025A's single-file `Wiki/Wiki.md` is live, conflict-aware, and tested but only covers the snapshot portion of the wiki vision. `context.md` lines 439-468 describe a multi-file Obsidian-style knowledge graph (`requirements.md`, `actors.md`, `workflows.md`, `entities.md`, `decisions.md`, `reports.md`, `sources.md` plus an index `Wiki.md` with `[[wiki links]]`). The encyclopedia structure is the spec-correct deliverable and will land before TC-027. | TC-025A, TC-025B, CURRENT, test index |
| 2026-05-28 | TC-025B encyclopedia wiki shipped (commit 23107b3) | Eight-file Obsidian-style wiki replaces the TC-025A single-file composer. Title-normalization routing of SAD sections to category files; `[[wiki links]]` in the index; YAML frontmatter on every note; per-file hash tracking; bulk conflict approval; backup of managed files to `_SADify/wiki-backups/<timestamp>/` before overwrite. Live Case 13 smoke passed. | TC-025B, CURRENT, test index |
| 2026-05-28 | Introduce TC-026D project isolation before TC-027 deploy | Current `SADify Projects/SAD/` and `Wiki/` are shared across all SADs in a connected repo; a second project overwrites the first's wiki and clutters the SAD folder. Per-project subfolders (`SADify Projects/<Project>/SAD/`, `/Wiki/`, etc.) with per-project SV-/SA-/SM- counters fix this. SP- IDs stay global because SadPreviewRepository and /sad/preview are out of scope. Drive `drive.file` scope means manually-created Drive folders aren't discoverable; documented limitation. | TC-026D plan, CURRENT, test index |
| 2026-05-28 | TC-026D project isolation shipped (commit 928d7f7) | Live Cases 15-19 manual smoke passed. Two real sibling project folders verified in Drive with their own SAD/ + Wiki/ trees. Per-project counters confirmed isolated. `CreateProjectDialog` auto-opens on PROJECT_REQUIRED. Frontend TypeScript token_store union fixed to include "secret_manager" (pre-existing TC-026B gap). 428 local-mode regression green. | TC-026D, CURRENT, test index |
| 2026-05-28 | Introduce TC-026E project save history before TC-027 deploy | Page refresh currently loses the saved-card UI state; backend retains save records in memory but the user can't see prior saves. `GET /projects/{project_id}/saves` plus a `ProjectHistoryPanel` exposes per-project history, persists across refresh, and auto-refreshes after each save. Future Firestore persistence routes through a single new `SadSaveRepository.list_for_project` method so the swap is one place. | TC-026E plan, CURRENT, test index |
| 2026-05-29 | TC-026E project save history shipped (commit 8f1a302) | Live Case 20 passed: history survives F5 refresh via auth-restore re-fetch of /drive/repo/status then /projects/{id}/saves; auto-refreshes after save; isolates per project (PR-000002 vs PR-000003). History endpoint is Drive-free, in-memory only. 446 local-mode regression green. | TC-026E, CURRENT, test index |
| 2026-05-29 | Open TC-029 analysis-state reset fix as next priority before TC-027 | Case 20 log proved analysis state is not reset per new source/project: AN-000012/13/14 stayed pinned at score=100 with all slots locked (source=fallback) after AN-000011 saturated, so a new catering source produced a pet-grooming-contaminated SAD. Unifies three symptoms (I'm-not-sure accepted, 100%-no-questions on complete source, cross-source content bleed) into one root cause: no per-source/per-project analysis-state reset boundary. Fix lives in analysis_state + carry-forward logic; Drive/save/wiki/project/history plumbing is unaffected. | TC-029 (pending plan), CURRENT, test index |
| 2026-05-29 | TC-029 shipped (commit 670b5b9) via explicit analysis_session_id | Frontend owns a session id, regenerated on new-source-upload / project-switch, sent on every analyze call. Backend keys latest_for_request on session id first (fresh when no match; no fall-through to text matching), preserving legacy guest-draft/base-text paths for requests without a session id. Live smoke: catering source after a saturated grooming analysis produced a genuine catering SAD with fresh Q&A (71% -> questions), no contamination. 457 local-mode tests; zero existing tests changed. | TC-029, CURRENT, test index |
| 2026-05-29 | Promote Firestore persistence to TC-030, a hard prerequisite before TC-027 deploy | In-memory repositories lose all state on Cloud Run scale-to-zero cold starts, across multiple instances, and on every redeploy -- so save history/projects would be unreliable in production, contradicting the requirement that history always persists. Firestore Native Mode is the canonical store already named in CLAUDE.md; the in-memory repos were always temporary stand-ins (TC-020 noted real Firestore deferred). Persist projects, saves, wiki state, and drive grant; analysis/Q&A state may stay in-memory as an ephemeral working session. | TC-030 (pending plan), CURRENT, test index |
| 2026-06-03 | Approved TC-032 Gemini model picker and reserved Layer 2 as TC-033 | P-009 is resolved by runtime Gemini-only selection with backend fallback; Layer 2 follows after picker | TC-032 spec/plan, CURRENT, test index |
| 2026-06-04 | TC-032 Gemini model picker locally passed; production smoke pending | Backend catalog returns Flash default, Pro, and Flash-Lite; Pro is supported through model-aware generation config; frontend picker loads dynamically from `/models`, persists selection, and threads the selected model into Q&A and SAD preview. Full suite 487 passed / 4 skipped; deploy and live-site Pro smoke remain gated by explicit approval | TC-032, CURRENT, test index, ae97f8e, e44951c |
| 2026-06-05 | Made `/agent/approve` deterministic after live GATE 3 reliability finding | Live testing showed the agent-driven approve path could regenerate a new preview and burn the token instead of saving the approved preview. The fix executes only approved actions, skips LLM re-run, consumes the token on success, keeps it on hard failure, and turns wiki conflict into re-approval | TC-034, CURRENT, test index, 639d043, 686e3de |
| 2026-06-05 | Added the P4 SSE activity timeline additively | `/agent/finalize/stream` emits NDJSON events with derived reasoning, and the frontend `AgentTimeline` consumes the POST stream with `fetch()` + `ReadableStream`. Manual flow remains untouched. Automated checks passed; browser smoke evidence is pending | TC-034, CURRENT, test index, d1285d2, 31d256d |
| 2026-06-05 | Superseded the earlier partial TC-034c browser-smoke note | An earlier localhost run only proved timeline reasoning/tool steps and stopped at clarification. Later TC-034c evidence superseded it with approval card, real Drive Doc save, wiki update, and wiki-conflict overwrite re-approval | TC-034, CURRENT, test index |
| 2026-06-05 | Recorded collaborative finalize and closed review -> revise loop decisions | The agent now trusts completed Q&A, treats review tighten/ask issues as draft open questions, feeds regenerate feedback into the next SAD draft, prevents redraw flailing, and keeps no-fabrication guardrails in the revise prompt | TC-034, CURRENT, test index, D-099, D-100, e0f9fd1, 0889aab |
| 2026-06-19 | Added durable GitHub issue relaunch with marker deduplication | Immutable issue sets survive restart in Firestore, relaunch always returns to GATE 3, sequential retries skip matching body markers, repository lock prevents silent retargeting, and the accepted concurrent race is explicit. Automated regression passed; live TC-036 smoke remains pending | TC-036, D-102, commits 074f17b..1d3fee2 |
| 2026-06-05 | Marked TC-034c browser smoke passed and recorded live Drive/wiki agent evidence | Live Flash browser smoke passed end-to-end: approval card appeared, `Approve & save` wrote a real Drive Doc and updated the wiki, wiki conflict returned overwrite re-approval, and the overwrite approval updated the wiki. Demo video, architecture writeup, deploy, and P5 MCP remain pending | TC-034, CURRENT, test index, bce7488, da153be |
