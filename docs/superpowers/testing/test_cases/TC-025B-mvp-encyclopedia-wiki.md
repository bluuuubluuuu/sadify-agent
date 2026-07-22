# TC-025B MVP Encyclopedia Wiki

Date Created: 2026-05-27
Last Updated: 2026-05-28
Status: Passed (live multi-file wiki + per-file conflict + backup verified end-to-end)

## Purpose

Replace the TC-025A single-file `Wiki/Wiki.md` snapshot with a multi-file
Obsidian-style knowledge wiki per `context.md` lines 439-468. After a SAD
save the user clicks **Update wiki** and SADify writes eight Markdown files
into `SADify Projects/Wiki/`: one categorized note per knowledge area
(`requirements.md`, `actors.md`, `workflows.md`, `entities.md`,
`decisions.md`, `reports.md`, `sources.md`) plus `Wiki.md` as the index
page that cross-links to every note via `[[wiki links]]`. Per-file hash
conflict detection and backups to `_SADify/wiki-backups/<timestamp>/`
make repeat updates safe.

## Inputs

- Live signed-in Firebase user with an active Drive grant.
- At least one prior live `SadSaveRecord` in the connected repo, plus a
  still-cached `SadPreviewRecord` for that save's `preview_id` (the
  wiki composer requires section bodies that live only on the preview).
- OAuth client secret in Secret Manager and refresh token in
  `sadify-drive-token-<uid>`.

## Preconditions

- TC-026B live Drive/Docs save passed (provides the `SadSaveRecord` and
  Drive folder).
- TC-025A snapshot wiki passed; its composer is being replaced here.
- Cloud setup per runbook `TC-026B Live Drive/Docs Setup` section.

## Scope

In scope:

1. Eight Markdown files written into `SADify Projects/Wiki/` on every
   update (index plus seven categorized notes).
2. Per-category content composition driven by `SadPreviewResponse.sections`
   resolved via `SadPreviewRepository.get_preview(latest_save.preview_id)`
   so section bodies are actually present (fixes the TC-025A section-
   summary collapse bug).
3. Title-normalization routing rule: each `SadPreviewSection.title` is
   lower-cased, punctuation stripped, whitespace collapsed, then matched
   against a fixed routing table to a wiki category. Unmatched sections
   go into `requirements.md` under "Other" so no SAD content is lost.
4. `[[wiki links]]` cross-references between notes (filename only,
   Obsidian convention).
5. YAML frontmatter on every note (`title`, `tags`, `updated_at`; index
   additionally carries `project_repo`, `repo_grant_id`, `latest_save_id`).
6. Per-file hash tracking via `WikiStateRepository` keyed by
   `(repo_grant_id, file_name)`.
7. Backup of the eight managed wiki files (only) to
   `_SADify/wiki-backups/<iso-timestamp>/` before any overwrite.
   First-time writes skip backup.
8. `POST /sad/wiki/preview` returns a list of `WikiFilePreview` entries
   plus aggregate `requires_confirmation` and `changed_files` payload.
9. `POST /sad/wiki/update` writes all eight files, returns per-file
   `WikiFileResult` plus `backup: WikiBackupInfo` and `updated_at`.
10. Bulk conflict approval: when any of the eight files has drifted in
    Drive, the dialog lists the changed files and requires a single
    **Overwrite all** confirmation.
11. Frontend `WikiUpdateDialog` rewritten to render the per-file diff
    list and offer bulk overwrite.

Out of scope:

- Per-file independent conflict approval. Bulk only.
- Drive Picker / folder browser. Project-isolation is TC-026D.
- Editing wiki notes from inside SADify. Edits happen in Drive (or
  download/edit/re-upload).
- Per-section partial save retry on mid-flight failure (retry the whole
  update).
- TC-027 Cloud Run deployment.

## Steps

1. Set live env (`SADIFY_DRIVE_MODE=live`, `SADIFY_DRIVE_LIVE_ENABLED=1`,
   `SADIFY_GOOGLE_OAUTH_CLIENT_ID=...`, `OAUTHLIB_RELAX_TOKEN_SCOPE` now
   defaulted in code).
2. Restart backend and frontend. Sign in. Connect Drive.
3. Upload source, run analysis to draft-ready, save SAD (real Doc
   created).
4. Click **Update wiki**.
5. On first-time encyclopedia write (no `Wiki.md` exists yet OR only the
   TC-025A `Wiki.md` exists), backend returns `requires_confirmation=true`
   only for the legacy `Wiki.md` if it's present. Frontend opens dialog,
   user clicks **Overwrite all** -> 8 files written, backup of any
   pre-existing managed files captured.
6. Open Drive, navigate to `SADify Projects/Wiki/`, confirm eight files
   exist with composed content. Verify YAML frontmatter and `[[wiki
   links]]` in `Wiki.md`.

## Expected Output

- `POST /sad/wiki/preview` returns a `files` list of exactly 8 entries
  in fixed order: Wiki.md, requirements.md, actors.md, workflows.md,
  entities.md, decisions.md, reports.md, sources.md.
- `POST /sad/wiki/update` writes all 8 files; response includes per-file
  `file_id` + `web_view_link` + hash + `created_new_file` flag, plus
  `backup` info.
- Stable rejection codes: `WIKI_AUTH_REQUIRED`, `WIKI_REPO_REQUIRED`,
  `WIKI_REPO_DISCONNECTED`, `WIKI_SAVE_REQUIRED`,
  `WIKI_LIVE_MODE_DISABLED`, `WIKI_REMOTE_READ_FAILED`, `WIKI_CONFLICT`
  (with `changed_files` payload), `WIKI_WRITE_FAILED`,
  `WIKI_BACKUP_FAILED`.
- Local-mode regression (`SADIFY_DRIVE_MODE=local`) stays at 387 tests
  green.

## Real Output

Implementation commit: `23107b3 feat(wiki): encyclopedia knowledge graph with per-file conflict and backup`.

Automated verification on 2026-05-27:
- Focused wiki tests (compose, state, backup, routes): 39 passed.
- Static wiki UI tests: 6 passed.
- Full Python regression with `SADIFY_DRIVE_MODE=local`: 387 passed.
- TypeScript `npx -y tsc --noEmit`: clean.

Live manual smoke on 2026-05-28 (Case 13, first encyclopedia write):

```text
POST /auth/session                  200
POST /drive/repo/connect            200  DG-000001 -> SADify Projects
POST /sources/upload                200
POST /analysis/requirement          200 x8 (some 502 Vertex 429s, recovered)
POST /sad/preview                   200  SP-000001
POST /sad/save                      200  SV-000001 / real Google Doc
                                          1jT_e-QEDD_-Zq6tF3-P7TWzf1RCT0ReRCSushQxu5sw
POST /sad/wiki/preview              200  requires_confirmation=true
                                          (legacy TC-025A Wiki.md detected as drifted)
POST /sad/wiki/update               200  8 files written, backup captured
                                          backup path: _SADify/wiki-backups/2026-05-28T03-03-15Z/
```

Saved-card and Drive verification:

```text
Wiki/Wiki.md                  Updated   1Zx1Lv91qiannrCAcPayKGmiOPACI5DKh
Wiki/requirements.md          Created   19zw7JW14yM5B3IWxz4MpbWFO2Kf1zT6a
Wiki/actors.md                Created   1ubFlLJeXEIZUoP1NoJUfbDTyiH9PcRQH
Wiki/workflows.md             Created   1Bc9CmH3aVz2kl1pqo1DHGm4LC5wGUJQi
Wiki/entities.md              Created   15FXkl55W3kgT_QAxaNiiyg3h3jmHFf9A
Wiki/decisions.md             Created   1op2uZdAH_qe7c3_Xv6It_vNcVyRhaYK-
Wiki/reports.md               Created   1eWugA-UrPVNE3NoqyEYxYZQCtw7_VAFe
Wiki/sources.md               Created   1JD2ls1KO9FFMiWnNxfXrkD45omSJl8qW

Backup: _SADify/wiki-backups/2026-05-28T03-03-15Z/  (1 file from TC-025A)

Wiki.md (index) opened in Drive shows:
- YAML frontmatter (title, tags, updated_at, project_repo, repo_grant_id,
  latest_save_id)
- Knowledge Notes section with [[requirements]], [[actors]], [[workflows]],
  [[entities]], [[decisions]], [[reports]], [[sources]] wiki links
- Save History with SV-000001 link to the real SAD Doc
```

## Differences / Issues

Case 14 (manual conflict drill) not run as a separate smoke. Case 13
incidentally exercised the conflict path because the prior TC-025A
`Wiki.md` was present at the start: backend correctly flagged it as
drifted (last_known_hash unknown after uvicorn restart), dialog opened,
overwrite-all wrote the eight encyclopedia files and backed up the
legacy `Wiki.md`. This validates the conflict + backup pipeline end-
to-end.

Polish items deferred:
- `_read_remote_wiki_files` downloads the full content of every existing
  wiki file on every preview + update call. Could use Drive's
  `md5Checksum` field to skip body download when hashing. Defer.
- Backup uses download-then-upload roundtrip per file. Drive's
  `files.copy` is faster. Defer.
- `WikiStateRepository` is in-memory only. uvicorn restart resets all
  `last_known_hash` values; the next preview will flag every existing
  remote file as drifted and trigger the conflict dialog spuriously.
  Persistence to Firestore is future work.

Known SAD content gap surfaced during Case 13 manual smoke (not a
TC-025B bug):
- Vertex AI 429 RESOURCE_EXHAUSTED during analysis turns. System
  fell back / retried correctly. Informational only.

## Evidence

- Implementation commit `23107b3` + subfolder fix already in `8e19296`.
- 39 mocked backend wiki tests + 6 frontend static tests + 387 full
  regression all green.
- TypeScript `--noEmit` clean.
- Live manual Case 13: all eight files in Drive with correct paths,
  YAML frontmatter, `[[wiki links]]`, backup directory present.
- No live Google calls happened with `SADIFY_DRIVE_MODE` unset.
- No refresh token or OAuth client secret in logs.

## Decision

Passed. The encyclopedia wiki replaces the TC-025A snapshot with a
real multi-file knowledge graph that matches `context.md` lines
439-468. Per-file conflict detection and backup-before-overwrite
protect user edits. The TC-025A composer is removed; only the
encyclopedia composer ships forward.

TC-026D project isolation is the next slice. The current TC-025B
implementation operates on a single shared wiki per repo; TC-026D
re-scopes the wiki to each project's own subfolder so multiple
projects can coexist without overwriting each other's wikis.
