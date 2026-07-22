# TC-026D MVP Project Isolation

Date Created: 2026-05-28
Last Updated: 2026-05-28
Status: Passed (per-project Drive isolation, counter scoping, wiki/save subfolder routing verified end-to-end)

## Purpose

Introduce a Project concept so a single connected `SADify Projects` Drive
folder can hold multiple isolated projects. Each project lives in its own
subfolder (`SADify Projects/<Project>/`) containing its own `SAD/`,
`Wiki/`, and `_SADify/wiki-backups/` subdirectories. Per-project `SV-`,
`SA-`, `SM-` counters reset independently; `SP-` (preview) stays globally
unique because `SadPreviewRepository` is out of scope.

## Inputs

- Live signed-in Firebase user with an active Drive grant.
- A connected `SADify Projects` repo folder.
- At least one SAD preview ready to save.
- Vertex AI Gemini for SAD synthesis (unchanged from prior phases).

## Preconditions

- TC-026B live Drive/Docs save passed.
- TC-025A snapshot wiki + TC-025B encyclopedia wiki passed.
- Cloud setup per runbook `TC-026B Live Drive/Docs Setup` section.

## Scope

In scope:

1. New `ProjectRepository` in-memory store and `ProjectRecord` model
   keyed by `(repo_grant_id, project_id)`.
2. New `DriveClient.list_subfolders(parent_folder_id)` helper.
3. New routes `GET /projects`, `POST /projects`, `POST /projects/switch`.
4. `DriveRepoRecord` extended additively with `active_project_id`,
   `active_project_name`, `available_projects`.
5. `/sad/save`, `/sad/wiki/preview`, `/sad/wiki/update` require an
   active project; resolve `SAD/`, `Wiki/`, `_SADify/` under the
   active project subfolder.
6. Per-project ID counters in `SadSaveRepository` keyed by
   `(grant_id, project_id)`. `SP-` (preview) stays global.
7. `WikiStateRepository` keyed by `(grant_id, project_id, file_name)`.
8. Wiki backup writes to `<Project>/_SADify/wiki-backups/<timestamp>/`.
9. Idempotency key for SAD save extended to include `project_id`.
10. Frontend `ProjectPanel` with dropdown + New project + Refresh
    buttons.
11. `CreateProjectDialog` auto-opens on `PROJECT_REQUIRED` /
    `WIKI_PROJECT_REQUIRED` 409 returns from save / wiki update.
12. Frontend `DriveRepoRecord.token_store` TypeScript union extended
    to include `"secret_manager"` (pre-existing TC-026B gap fixed in
    the same commit).

Out of scope (deferred):

- Discovery of folders manually created in Drive UI under
  `SADify Projects/`: `drive.file` scope cannot see them. Documented
  limitation; Drive Picker / broader scope is future work.
- Editing wiki notes from inside SADify.
- Project rename / delete from the SADify UI (do it in Drive).
- Cross-project bulk operations.
- Schema changes to `SadSaveRecord`, `SadSaveManifest`,
  `SadSaveArtifact`, or wiki models.
- TC-027 Cloud Run deployment.

## Steps

1. Sign in live, connect Drive, confirm the `Projects` panel renders
   empty.
2. Upload a source, run analysis to draft-ready, generate SAD preview,
   click **Save to project repo**.
3. Backend returns 409 `PROJECT_REQUIRED`; frontend opens
   `CreateProjectDialog` with a suggested name from the preview title.
4. User edits the name (regex `^[A-Za-z0-9 _\-]+$`, max 80 chars),
   clicks **Create project** -> `POST /projects 200` then save retries
   automatically.
5. Click **New project**, name a second project, save the same preview
   into it. Confirm SAD doc lands in the new project's subfolder with
   `SV-000001` (per-project counter reset).
6. Switch to project 1 via dropdown, click **Update wiki**. Confirm 8
   wiki files land in project 1's `Wiki/`. Switch to project 2, repeat.
   Confirm each project's wiki tree is independent.
7. Regenerate the SAD preview (global `SP-000002`), save in each
   project. Confirm both projects show `SV-000002`.
8. Click **Refresh** in the Projects panel. Both projects still appear.

## Expected Output

- `GET /projects 200` returns the list of projects with active state.
- `POST /projects 200` creates a project folder in Drive (live mode) or
  with a fake folder ID (local mode) and sets it active.
- `POST /projects/switch 200` updates active state.
- `POST /sad/save 409 PROJECT_REQUIRED` when no active project.
- `POST /sad/wiki/preview 409 WIKI_PROJECT_REQUIRED` when no active
  project.
- `POST /sad/save 200` writes the SAD doc into
  `<Project>/SAD/SAD-<preview>-<save>.google_doc`.
- `POST /sad/wiki/update 200` writes 8 files into `<Project>/Wiki/`
  and backups (if any) into `<Project>/_SADify/wiki-backups/<ts>/`.
- Counter isolation: same `SV-000001` in two projects is two different
  real Docs.

## Real Output

Implementation commit: `928d7f7 feat(projects): per-project Drive
isolation with active project switching`.

Automated verification on 2026-05-28:

- Backend regression with `SADIFY_DRIVE_MODE=local`: **428 passed**
  (was 387 before TC-026D; +41 new tests).
- Frontend `npx -y tsc --noEmit`: clean.
- 28 new test functions across `test_projects.py`,
  `test_drive_client_list_subfolders.py`, and `test_mvp_project_ui.py`,
  plus updates to `test_drive_repo*`, `test_sad_save*`, `test_wiki_*`.

Live manual smoke on 2026-05-28:

```text
Case 15  first project create + save
  POST /auth/session                       200
  POST /drive/repo/connect                 200  DG-000001
  POST /sources/upload                     200
  POST /analysis/requirement x12           200  draft-ready
  POST /sad/preview                        200  SP-000001
  POST /sad/save                           409  PROJECT_REQUIRED (dialog opens)
  POST /projects                           200  PR-000001 "Pet Grooming Appointments"
  POST /sad/save                           200  SV-000001 / real Doc
                                                1HOzWoeH2usRKqQlBvgArq28Nb6T5MxoP9tEozUuPciA
  Drive: SADify Projects/Pet Grooming Appointments/SAD/SAD-SP-000001-SV-000001

Case 16  second project alongside
  POST /projects                           200  PR-000002 "Catering Events"
  POST /sad/save                           200  SV-000001 (per-project counter)
                                                Different Doc ID from project 1
  Drive: SADify Projects/Catering Events/SAD/SAD-SP-000001-SV-000001
  Both sibling folders confirmed.

Case 17  project switch + per-project wiki update
  POST /projects/switch                    200  -> Pet Grooming
  POST /sad/wiki/preview                   200  requires_confirmation=false
  POST /sad/wiki/update                    200  8 files in Pet Grooming/Wiki/
  POST /projects/switch                    200  -> Catering Events
  POST /sad/wiki/preview                   200  requires_confirmation=false (per-project state)
  POST /sad/wiki/update                    200  8 files in Catering Events/Wiki/

Case 18  counter isolation across saves
  POST /sad/preview                        200  SP-000002 (global counter advanced)
  POST /sad/save (Pet Grooming)            200  SV-000002 in Pet Grooming
                                                Real Doc 15vs3KfKf9RqTjTAcVkzG93RSLjgElK1rS8Teaa-76VY
  POST /projects/switch                    200  -> Catering Events
  POST /sad/save (Catering Events)         200  SV-000002 in Catering Events
                                                Real Doc 1sqaPJJNQ2v85cbtxPRlhBC9gaD3ezxpnsQoYudLF_Us
  Both projects independently advanced from SV-000001 to SV-000002.

Case 19  app-created project discovery via Refresh
  GET /projects                            200  Dropdown still shows both projects.
                                                Note: drive.file scope cannot see folders manually
                                                created in Drive UI; documented limitation.
```

Final Drive structure (verified by user):

```text
SADify Projects/
  Pet Grooming Appointments/
    SAD/
      SAD-SP-000001-SV-000001.google_doc   (Doc 1HOzWoeH...)
      SAD-SP-000002-SV-000002.google_doc   (Doc 15vs3KfK...)
    Wiki/
      Wiki.md, requirements.md, actors.md, workflows.md,
      entities.md, decisions.md, reports.md, sources.md
  Catering Events/
    SAD/
      SAD-SP-000001-SV-000001.google_doc   (Doc 1sqaPJJN..., different from above)
      SAD-SP-000002-SV-000002.google_doc
    Wiki/
      Wiki.md, requirements.md, actors.md, workflows.md,
      entities.md, decisions.md, reports.md, sources.md
```

## Differences / Issues

1. **Drive `drive.file` scope limitation** (documented). Folders created
   manually in Drive UI under `SADify Projects/` are not visible to
   `files.list`. The Refresh button only re-syncs app-created projects.
   Drive Picker integration is a candidate post-MVP slice (potentially
   TC-026F).
2. **`CreateProjectDialog` renders inline** at the bottom of the page
   rather than as a centered modal overlay. Minor UX nit; functional.
3. **`change_summary` text on saved card** still reads "saved to SADify
   Projects as Google Doc" rather than mentioning the project name. The
   composer is project-agnostic. Defer to a polish slice.
4. **Suggested project name from SAD title** contains parentheses
   (e.g., "(AN-000012)") which fail the validation regex. User must
   edit the name. Frontend could pre-sanitize the suggestion; defer.
5. **`WikiStateRepository` still in-memory** (deferred from TC-025B).
   uvicorn restart wipes per-file hashes; next preview will flag remote
   files as drifted spuriously. Firestore persistence is post-MVP.

## Evidence

- Implementation commit `928d7f7`.
- 428 mocked backend tests + frontend static tests + TS clean.
- 5 live manual smoke cases (15-19) passed end-to-end on real Drive.
- Two real sibling project folders verified in `SADify Projects/`,
  each with their own `SAD/` and `Wiki/` trees, each holding their own
  pair of real Google Docs at `SV-000001` and `SV-000002`.
- Idempotency confirmed: parallel saves into two different projects
  with the same preview produce distinct Drive files; same preview into
  same project returns the cached record.
- No refresh tokens or OAuth client secrets appear in logs.

## Decision

Passed. SADify now supports multiple isolated projects per Drive grant.
Each project has its own SAD save folder, wiki tree, and backup
directory. Counters reset per project (SV-/SA-/SM-) while SP- preview
IDs remain globally unique. Idempotency keys correctly include the
project ID, preventing cross-project save collisions. The frontend
auto-creates a project on first save when no active project exists.

Next phase 5/6 slice: TC-026E project save history (per-project save
list endpoint + history UI), then TC-027 Cloud Run deploy.
