# TC-030 Firestore Persistence

Date Created: 2026-05-30
Last Updated: 2026-05-30
Status: Passed (automated + live round-trip + live restart-survival)

## Purpose

Make project, SAD-save, wiki-state, and Drive-grant data survive Cloud Run
cold starts, multiple instances, and redeploys by persisting the backing
repositories to Firestore Native Mode. Before this slice every backend
repository was in-memory, so a deployed service would lose all save
history/projects on scale-to-zero, across instances, and on every redeploy.
Firestore Native Mode is the documented canonical store (CLAUDE.md), so this
finishes a planned-but-deferred layer rather than adding scope. It is a hard
prerequisite for TC-027 deploy.

## Scope

In scope (persisted to Firestore):
- `ProjectRepository`, `SadSaveRepository`, `WikiStateRepository`,
  `DriveRepoRepository`.
- `SADIFY_PERSISTENCE=memory|firestore` flag (default `memory`); `memory`
  keeps the full offline test suite and local dev unchanged.
- Firestore document schema + transactional ID counters per repository.
- Mocked-client unit tests + an opt-in live round-trip smoke
  (`SADIFY_FIRESTORE_LIVE=1`).

Out of scope (intentionally in-memory):
- `RequirementAnalysisRepository` and source uploads — ephemeral working
  session; resetting on backend restart is correct.
- Any Pydantic API model / endpoint contract / frontend change.
- TC-027 Cloud Run deploy (separate slice this unblocks).

## Design

Each persisted repository became a small interface (Protocol) with two
implementations: the existing in-memory class (unchanged default) and a new
Firestore-backed class. `main.py` selects the implementation from
`config.persistence_mode`; injected repositories still take precedence (tests
pass fakes). Firestore repos read-through on demand (no in-memory cache), so
every instance reads the same source of truth. Serialization uses Pydantic
`model_dump(mode="json")` / `model_validate`; `WikiState` (a frozen dataclass)
uses explicit dict serialization. ID counters (PR-/SV-/SA-/SM-/DG-/fake-doc/
local-folder) are allocated through Firestore transactions so concurrent
instances cannot collide; counter "gaps" on a rare abort are accepted
(uniqueness over contiguity).

Firestore collections:

```text
drive_repos/{grant_id}                     (+ owner_uid, active flag)
projects/{grant_id}__{project_id}          (+ grant_id, order)
project_name_index/{grant_id}__{name_hash} (deterministic same-name dedup)
sad_saves/{grant_id}__{project_id}__{save_id}
sad_save_idempotency/{sha256(idempotency_key)}
wiki_state/{grant_id}__{project_id}__{file_name}
counters/{scope}                           (transactional sequence docs)
```

## Implementation Commits

```text
969cad8 feat(persistence): firestore-backed repositories behind SADIFY_PERSISTENCE
21616c7 fix(persistence): begin firestore transactions via transactional decorator
c2166cd test(persistence): live firestore smoke for save/wiki/drive-grant round-trips
```

## P0 Defects Found In Review (both fixed in 21616c7)

The initial implementation (969cad8) passed its mocked unit tests but had two
P0 bugs that only fail against real Firestore — invisible to the mock:

1. `FirestoreSadSaveRepository.save_preview` interleaved counter reads and
   writes inside one transaction. Firestore requires all reads before any
   writes; this raised `400 read after write`.
2. The manual transaction pattern (`client.transaction()` ->
   `ref.get(transaction=...)`) never called `_begin()`. Against real
   google-cloud-firestore 2.27.0, `get_transaction_id` raises
   `ValueError: Transaction not in progress` on the first transactional read,
   and bare `transaction.commit()` resolved to `WriteBatch.commit`, not the
   transaction commit. This affected every counter, `create_project`, and
   `save_preview`.

Fix: a `run_in_transaction(client, func)` helper applies the official
`firestore.transactional` decorator (which performs `_begin`/`_commit`/retry).
All three transactional bodies route through it; counters allocate before the
final save transaction so reads precede writes. The test `FakeTransaction` was
upgraded to model the decorator lifecycle (`_clean_up`/`_begin`/`_commit`/
`_rollback`/`in_progress`/`_read_only`/`_max_attempts`) and to reject a read
after a write — so the mocked suite now exercises the real decorator control
flow and guards this bug class going forward. Reviewed and PASS by both Claude
and Codex.

## Cloud Prerequisites (verified in GCP console for project `sadify`)

- Firestore `(default)` database: **Native mode**, Standard edition,
  `asia-southeast1` (created 2 May 2026). Confirmed 2026-05-30.
- IAM `roles/datastore.user`:
  - `sadify-agent-sa@sadify.iam.gserviceaccount.com` (Cloud Run runtime) —
    already held.
  - `firebase-adminsdk-fbsvc@sadify.iam.gserviceaccount.com` (local dev via
    `GOOGLE_APPLICATION_CREDENTIALS`) — **granted 2026-05-30** for the live
    smoke.

## Configuration

```text
SADIFY_PERSISTENCE=memory     # default; set "firestore" in deployed/live-persist runs
SADIFY_FIRESTORE_LIVE=        # leave empty; set 1 only for the opt-in live smoke
```

New backend dependency: `google-cloud-firestore` (2.27.0, already present
locally) — the only new dependency.

## Expected Output

- Default `memory` mode: byte-identical behavior; full suite unchanged.
- `firestore` mode: projects/saves/wiki-state/drive-grant persist and reappear
  after a backend restart; analysis/Q&A intentionally reset.
- Mocked unit tests pass; live round-trip writes then reads back each record
  against real Firestore; live restart-survival proves data returns on a cold
  process.

## Real Output

Automated verification on 2026-05-30 (`SADIFY_DRIVE_MODE=local`,
`SADIFY_PERSISTENCE` unset):

```text
Full Python regression: 471 passed, 4 skipped (the 4 live smoke tests skip
  without SADIFY_FIRESTORE_LIVE=1; imports still resolve at collection).
TypeScript npx -y tsc --noEmit: clean (no frontend change).
Default memory-mode behavior byte-identical; zero existing tests modified.
Firestore unit tests (mocked client, decorator-driven): 14 passed.
```

Live round-trip smoke (Task 7.3, `SADIFY_FIRESTORE_LIVE=1`,
`GOOGLE_CLOUD_PROJECT=sadify`, firebase-adminsdk credential) — real Firestore:

```text
4 passed:
  test_firestore_live_project_round_trip   (create/get/get-by-name/list)
  test_firestore_live_sad_save_round_trip  (save_preview txn + get + list + idempotency)
  test_firestore_live_wiki_state_round_trip(record/get/get_all/clear)
  test_firestore_live_drive_repo_round_trip(connect/get_active/get_latest/set_active_project)
Each test self-cleans per-run docs; global sequence counters intentionally left.
```

Live restart-survival smoke (Task 7.4, real app, `SADIFY_PERSISTENCE=firestore`
+ `SADIFY_DRIVE_MODE=local`) on 2026-05-30:

```text
Case 1: backend booted in firestore mode, no Firestore/credential error;
        GET /drive/repo/status 200 issued a live Firestore query.
Case 2: connect Drive -> grant DG-000002 (wrote drive_repos); create project
        Pet grooming -> PR-000001 (wrote projects); saves query 200 (empty).
Case 3: Q&A to 100% -> SAD preview SP-000002 -> Save -> SV-000001
        (POST /sad/save 200 ran the save_preview transaction live; coherent
        pet-grooming SAD, no contamination).
Case 4: Update wiki -> "disabled for this process" (expected in local Drive
        mode; wiki-state persistence covered by the 7.3 automated live test).
Case 5 (the proof): Ctrl+C backend -> relaunch (fresh PID 1572) -> refresh.
        Project (PR-000001), save history (SV-000001), and Drive grant
        (DG-000002, Save access Allowed) all REAPPEARED from Firestore.
        Sources/analysis/preview correctly reset (in-memory ephemeral state).
```

## Differences / Issues

- Benign `UserWarning: Detected filter using positional arguments` from
  `.where(field, op, value)` calls (library deprecation). Non-blocking;
  optional future cleanup to keyword `filter=`.
- Benign Windows `ConnectionResetError [WinError 10054]` /
  `_call_connection_lost` asyncio noise when the browser closes a socket
  early. Not an app or Firestore error.
- Wiki update is disabled in local Drive mode by design (live wiki writes
  need `SADIFY_DRIVE_MODE=live`); wiki-state Firestore persistence is proven
  by the automated live round-trip instead.

## Evidence

- Commits `969cad8`, `21616c7`, `c2166cd`.
- 471 passed / 4 skipped offline; 14 mocked Firestore tests; TS clean.
- Library-source verification of both P0s in
  `google/cloud/firestore_v1/_helpers.py:1016` (INACTIVE_TXN) and
  `transaction.py` (`transactional`, `_begin`/`_commit`).
- Standalone guard proof: read-after-write raises; valid read->write path
  begins/commits/persists through the real decorator.
- Live 7.3: 4 round-trips passed against real Firestore.
- Live 7.4: cold-restart UI + fresh-PID backend log showing project/save/grant
  survived.
- Dual review (Claude + Codex) PASS on the transaction hardening and the
  extended live smoke.

## Decision

Passed. Project, SAD-save, wiki-state, and Drive-grant data now persist to
Firestore Native Mode behind `SADIFY_PERSISTENCE=firestore` and survive a cold
backend restart; analysis/Q&A intentionally stays ephemeral. Default `memory`
mode is byte-identical and keeps offline tests/dev unchanged. The deploy
blocker (in-memory state loss) is resolved. Next: TC-027 two-service Cloud Run
deploy (runs `SADIFY_DRIVE_MODE=live` + `SADIFY_PERSISTENCE=firestore`).
