# TC-015 Prototype-To-MVP Design Alignment

Date Created: 2026-05-11
Last Updated: 2026-05-11
Status: Passed

## Purpose

Verify that the prototype-to-MVP design, decision log, development index, workflow, and test index agree before MVP code changes begin.

## Inputs

- `docs/superpowers/specs/2026-05-11-sadify-prototype-to-mvp-design.md`
- `docs/superpowers/development/00_development_index.md`
- `docs/superpowers/development/05_development_workflow.md`
- `docs/superpowers/development/07_decision_log.md`
- `docs/superpowers/testing/test_case_index.md`

## Preconditions

Prototype baseline tests pass.

## Steps

1. Run API/docs preflight for the checkpoint.
2. Review the design spec.
3. Confirm superseded prototype decisions are explicitly marked.
4. Confirm MVP checkpoint rows exist in the workflow and test index.
5. Confirm no code or cloud changes are included in this checkpoint.

## Expected Output

Planning docs agree on the Next.js + FastAPI MVP direction and the first thin full-stack slice.

## Real Output

Passed. MVP-00 is documentation-only, so no external API, SDK, OAuth, cloud service, or browser integration docs needed to be fetched before executing this checkpoint.

The design, decision, workflow, index, and test docs agree on the prototype-to-MVP direction:

- MVP target is Next.js/React frontend plus Python FastAPI backend.
- Streamlit remains the proven prototype path, not the MVP foundation.
- Service-account shared-folder Drive behavior is marked superseded for MVP.
- MVP workflow contains MVP-00 through MVP-12.
- Test index contains TC-015 through TC-027.
- Implementation plan and MVP test plan are present.

## Differences / Issues

No blocking alignment issues found.

Notes:

- The phrase "Share Drive folder with service account" still appears in the decision log, but only as an explicitly superseded prototype decision.
- The same phrase appears in the implementation plan because it is part of the consistency-search command itself.
- No code, dependency, API, IAM, OAuth, Firebase, Drive, Docs, or Cloud Run change was made during this checkpoint.

## Evidence

API/docs preflight:

```text
External API/docs fetch required: no
Reason: MVP-00 validates planning documents only.
Network/cloud access required: no
User approval for API/cost/IAM/deployment: not required for this checkpoint
```

Doc consistency command:

```powershell
rg -n "Streamlit for fastest MVP build|One Cloud Run service for MVP deployment|Share Drive folder with service account" docs\superpowers
```

Result summary:

```text
docs\superpowers\development\07_decision_log.md:
D-035 marks "Share Drive folder with service account..." as Superseded for MVP.

docs\superpowers\archive\plans\consolidated-plans.md:
The phrase appears only inside the consistency-search command.
```

Alignment command:

```powershell
rg -n "Next.js/React|Python FastAPI|MVP-00|MVP-12|TC-015|TC-027|service-account Drive|Superseded for MVP|OAuth/Firebase/IAM" docs\superpowers\specs\2026-05-11-sadify-prototype-to-mvp-design.md docs\superpowers\development\00_development_index.md docs\superpowers\development\04_google_cloud_setup_runbook.md docs\superpowers\development\05_development_workflow.md docs\superpowers\development\07_decision_log.md docs\superpowers\testing\test_case_index.md
```

Result summary:

```text
The design spec, development index, workflow, decision log, and test case index all contain the expected MVP direction and checkpoint references.
```

Required planning files:

```powershell
Test-Path docs\superpowers\specs\2026-05-11-sadify-prototype-to-mvp-design.md
Test-Path docs\superpowers\archive\plans\consolidated-plans.md
Test-Path docs\superpowers\testing\mvp_web_app_test_plan.md
```

Result:

```text
True
True
True
```

## Decision

Passed. Proceed to MVP-01 only after user approval.
