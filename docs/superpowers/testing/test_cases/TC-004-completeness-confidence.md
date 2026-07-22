# TC-004 Completeness + Confidence

Date Created: 2026-04-30
Last Updated: 2026-05-06
Status: Passed

## Purpose

Verify local completeness and confidence scoring before any live model-heavy analysis loop.

## Traceability Sources

- `docs/superpowers/development/05_development_workflow.md` - Checkpoint 7
- `docs/superpowers/development/02_agent_behavior_contract.md` - completeness and confidence behavior
- `docs/superpowers/development/01_product_scope.md` - completeness and confidence behavior
- `docs/superpowers/testing/test_case_index.md`

## Inputs

Requirement contexts with different levels of detail.

## Preconditions

Completeness engine exists. Live Gemini/model-router explanation is not required for this checkpoint and should remain a later slice unless explicitly approved.

## Steps

1. Submit a vague requirement.
2. Submit a partially detailed requirement.
3. Submit a strong requirement.
4. Compare scores, labels, missing information, confidence reasons, and practical business questions.

## Expected Output

- vague requirements score low and show critical missing areas
- partial requirements score partial/good and explain what is still unclear
- strong requirements score strong when the main business details are present
- confidence reason is understandable and based on visible evidence
- missing categories and business-friendly confirmation questions are listed
- no live model call is needed to pass this checkpoint

## Real Output

- `score_requirement_context("admin")` stays low, returns `Low` readiness/confidence, and places `Business problem` as the first missing area.
- Partial operational text scores in the middle range, returns visible evidence categories, and lists practical missing areas.
- Strong operational text scores `Strong` with `High` confidence without a live model call.
- `analyze_requirement_text` now exposes `scoring_basis` and `evidence_summary` for the Streamlit UI.
- Streamlit rendering shows a collapsed `Why this score` section with the local scoring basis and evidence summary.

## Differences / Issues

- No live Gemini/model-router explanation was used in this checkpoint. This is intentional for cost-safe local validation.
- The previous early heuristic could over-score role-only input such as `admin`; the new score cap keeps that input low until real business context is provided.

## Evidence

```text
Command: .\.venv\Scripts\pytest.exe tests\test_completeness_scoring.py tests\test_requirement_analysis.py tests\test_app_shell.py
Result: 19 passed in 0.57s
```

```text
Command: .\.venv\Scripts\pytest.exe
Result: 62 passed in 8.03s
```

## Decision

Passed for Checkpoint 7 local completeness + confidence scoring.

Continue to Checkpoint 8: relationship linking / knowledge graph.
