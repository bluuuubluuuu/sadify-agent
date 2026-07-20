# TC-025A MVP Wiki Snapshot

Date Created: 2026-05-11 (as TC-025)
Renamed and Updated: 2026-05-27
Status: Passed (live snapshot path verified end-to-end)

## Note

This test case was originally TC-025. After implementation it became clear
that the single-file `Wiki/Wiki.md` snapshot delivered here covers only the
snapshot portion of the wiki vision; the multi-file Obsidian-style
knowledge graph documented in `context.md` lines 439-468 (categorized
`requirements/`, `entities/`, `workflows/`, `decisions/`, `actors/`,
`reports/`, `sources/` notes with YAML frontmatter and `[[wiki links]]`)
is now a separate checkpoint TC-025B.

TC-025A captures what was actually built and shipped on 2026-05-26:
a live, conflict-aware, single-file wiki snapshot at `Wiki/Wiki.md`.

## Purpose

Verify that after a successful live SAD save, a project user can publish a
single-file Markdown snapshot to `Wiki/Wiki.md` inside the connected
`SADify Projects` Drive folder, with conflict-aware overwrite protection
when the remote file has changed since SADify last wrote it.

## Inputs

- Live signed-in Firebase user with an active Google Drive grant.
- At least one prior live SAD save (`SadSaveRecord` with
  `token_store="secret_manager"`) in the connected project repo.
- OAuth client secret in Secret Manager.
- Refresh token in `sadify-drive-token-<uid>`.

## Preconditions

- TC-019 live Firebase sign-in passed.
- TC-021 / TC-028 / Cycles 2A+2B passed for Q&A and SAD synthesis.
- TC-026B live Drive/Docs save passed (provides the `SadSaveRecord`
  that the wiki snapshot summarises).
- Cloud setup per runbook `TC-026B Live Drive/Docs Setup` section is
  in place; no new cloud prerequisites for TC-025A.

## Scope

In scope:

1. New backend services `wiki_compose` and `wiki_state` (in-memory hash
   tracker keyed by `repo_grant_id`).
2. New Drive client text-file helpers: find / download / upload-or-replace,
   plus subfolder support on `find_or_create_folder` via optional
   `parent_folder_id`.
3. New endpoints `POST /sad/wiki/preview` and `POST /sad/wiki/update`,
   live-mode-only behind the existing `SADIFY_DRIVE_MODE=live` +
   `SADIFY_DRIVE_LIVE_ENABLED=1` double gate.
4. Frontend **Update wiki** action on `SadPreviewPanel` after a SAD save
   succeeds, plus a `WikiUpdateDialog` component that renders the
   proposed vs current text on remote drift.
5. Wiki content writes into `SADify Projects/Wiki/Wiki.md` (Markdown
   file, not a Google Doc).
6. Hash-based conflict detection: when remote hash != last-known hash
   AND `force_overwrite=false` AND `remote_exists=true`, the update
   endpoint returns 409 `WIKI_CONFLICT`.

Out of scope (deferred to TC-025B):

- Multi-file categorized wiki (requirements / entities / workflows /
  decisions / actors / reports / sources subdivisions).
- Obsidian-style `[[wiki links]]` between notes.
- YAML frontmatter on wiki notes.
- Per-section content composers driven by SAD section bodies.
- Backups under `_SADify/wiki-backups/`.
- Per-file independent conflict approval.

## Steps

1. Sign in live, connect Drive (live mode, real OAuth grant).
2. Upload a source, run analysis to draft-ready, generate a SAD preview,
   save it (real Google Doc created).
3. Click **Update wiki** on the SAD preview panel.
4. Confirm `POST /sad/wiki/preview 200` then `POST /sad/wiki/update 200`.
5. Open Drive, navigate to `SADify Projects/Wiki/Wiki.md`, confirm the
   file exists with composed content.
6. (Mocked, not manual): hash mismatch + `force_overwrite=false` returns
   409 `WIKI_CONFLICT`; mocked test
   `test_wiki_update_blocks_on_conflict_when_force_false` proves the
   contract. Mocked test
   `test_wiki_update_overwrites_when_force_true` proves the overwrite
   path. Manual conflict smoke was not possible because Google Drive's
   web UI does not provide in-place editing for `.md` files.

## Expected Output

- `POST /sad/wiki/preview` returns 200 with `proposed_markdown`,
  `remote_hash`, `last_known_hash`, `requires_confirmation`,
  `remote_exists`, and `remote_markdown` (only when confirmation is
  required).
- `POST /sad/wiki/update` returns 200 with `wiki_path: "Wiki/Wiki.md"`,
  `wiki_url`, `wiki_file_id`, `wiki_hash`, `updated_at`,
  `created_new_file`.
- `Wiki/` subfolder is created on first use under the project repo
  folder; subsequent calls reuse the same folder.
- Stable rejection codes: `WIKI_AUTH_REQUIRED`, `WIKI_REPO_REQUIRED`,
  `WIKI_REPO_DISCONNECTED`, `WIKI_SAVE_REQUIRED`,
  `WIKI_LIVE_MODE_DISABLED`, `WIKI_REMOTE_READ_FAILED`, `WIKI_CONFLICT`,
  `WIKI_WRITE_FAILED`.

## Real Output

Implementation commits:
- `0b1ad4b feat(wiki): live wiki update with conflict-aware approval`
- `8e19296 fix(wiki): write Wiki.md into Wiki/ subfolder instead of project root`

Automated verification on 2026-05-26:
- Backend wiki slice (focused): 32 passed.
- Full Python regression with `SADIFY_DRIVE_MODE=local`: 374 passed.
- Frontend TypeScript `npx -y tsc --noEmit`: clean.
- 5 new wiki UI static tests; 2 new wiki subfolder route tests; 6 new
  Drive folder subfolder tests.

Live manual smoke on 2026-05-27 (Case 11, first-time wiki write):

```text
POST /auth/session                  200
POST /drive/repo/connect            200  DG-000002 -> SADify Projects
POST /sources/upload                200
POST /analysis/requirement (x11)    200  draft-ready reached (score 100)
POST /sad/preview                   200  SP-000002
POST /sad/save                      200  SV-000002 / real Google Doc
                                          1NskhXQwmTnTT7mmCcAfR2wxrsKlTHLhGMSBGRGG4evw
POST /sad/wiki/preview              200  requires_confirmation=false (first-time)
POST /sad/wiki/update               200  Wiki/Wiki.md created
                                          file_id=1Zx1Lv91qiannrCAcPayKGmiOPACI5DKh
                                          sha256:3ee5f7fe02b3ea9095066a119f3926caad56ba223e912664ded5aa541bdc5e87
```

Drive verification:

```text
Wiki path:   Wiki/Wiki.md  (inside SADify Projects/Wiki subfolder)
Wiki URL:    https://drive.google.com/file/d/1Zx1Lv91qiannrCAcPayKGmiOPACI5DKh/view
Drive shows: SADify Projects/Wiki/Wiki.md with composed Markdown content
             (project header, latest SAD link, requirement, sources,
              save history).
```

## Differences / Issues

1. The single-file flat snapshot does not satisfy the original
   `context.md` wiki vision (multi-file Obsidian-style knowledge graph
   under `wiki/requirements/`, `wiki/entities/`, etc.). The encyclopedia
   structure is now tracked as TC-025B and will be built before TC-027.
2. Section summaries in `Wiki.md` collapse to a single aggregate line
   `**SAD Preview for <analysis>:** N sections saved for this SAD
   preview.` instead of one bullet per SAD section with its first-sentence
   summary. The composer iterates SAD-section-count rather than
   SAD-section-content. Considered throwaway because TC-025B replaces the
   composer wholesale; no fix planned in TC-025A.
3. Case 12 manual conflict smoke not run. Google Drive's web preview
   does not support in-place `.md` editing. Mocked tests cover the
   contract.

## Evidence

- 32 mocked backend wiki tests pass; 5 frontend static tests pass; full
  regression 374 passed; TypeScript clean.
- Live manual Case 11: all backend logs show 200, `Wiki/` subfolder
  created in real Drive, real `Wiki.md` file rendered with composed
  Markdown structure.
- Subfolder fix `8e19296` verified by direct Drive inspection (file is
  inside `SADify Projects/Wiki/`, not at the project root).
- No live Google calls happen with `SADIFY_DRIVE_MODE` unset.

## Decision

Passed for the snapshot scope. The flat `Wiki/Wiki.md` write path is
shipped, conflict-aware, hash-tracked, and verified live. The richer
multi-file knowledge-graph wiki promised by `context.md` is tracked
separately as TC-025B and will be built before TC-027 Cloud Run deploy.
