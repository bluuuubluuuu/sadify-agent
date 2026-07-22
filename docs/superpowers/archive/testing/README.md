# SADify — Archived Test Cases

Superseded test cases preserved for historical reasoning, not for
active work.

Date archived: 2026-05-24
Last updated: 2026-05-25

## What's here

```text
test_cases/
  consolidated-test-cases.md
```

## Why these were archived

The consolidated test-case record contains the full TC-021R through TC-021Y
iteration trail. Those eight cases captured the Q&A and SAD quality fixes
between 2026-05-15 and 2026-05-21. The underlying problem each one tried to
address was eventually subsumed by:

- `testing/test_cases/TC-028-evidence-based-readiness.md` —
  unified evidence-based readiness model that replaced the
  keyword/phrase scoring these cases worked around.
- Cycle 2A (commits `f4faabb`, `8333f21`) — monotonic score,
  applicability stickiness, merged slot_evidence persistence.
- Cycle 2B (commit `c928b83`) — SAD section coverage,
  assumptions/open-questions population, paraphrasing,
  understanding-summary preservation.
- Anti-repetition Guard B at threshold 2 (commit `4a3f288`).

Manual browser smoke on 2026-05-24 against both the laundry and
event-rental PDFs confirmed the issues these archived cases tracked
no longer reproduce.

## When to open these files

Only when:

1. Tracing a past design decision (e.g. "why did we try X first?").
2. Investigating a regression that looks like one of the archived
   symptoms.
3. Writing post-mortem or demo narration that needs to cite the
   iteration trail.

For active work, follow `docs/superpowers/CURRENT.md` and the active
test cases listed in `docs/superpowers/testing/test_case_index.md`.
