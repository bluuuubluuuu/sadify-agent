# TC-026 Local SAD Save Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the local/fake SAD save path so a signed-in user with an active project repo can save an existing `SP-` SAD preview as a durable local artifact record without live Google Drive, Google Docs, OAuth exchange, Secret Manager writes, dependency additions, or deployment.

**Architecture:** Extend the current FastAPI `/sad` router with an authenticated `POST /sad/save` endpoint. The endpoint validates the signed-in user, active Drive repo state, and preview record, then uses a new in-memory `SadSaveRepository` plus artifact composer to produce a fake Google Doc artifact, `_SADify` manifest, change log, source references, and idempotent save record. The Next.js frontend adds one save action after preview generation and displays saved status or stable backend errors.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, in-memory fake stores, pytest, Next.js/React, TypeScript. No new Python or npm dependencies.

---

Date: 2026-05-25

Status: Draft - awaiting approval

## Traceability Sources

- `CLAUDE.md`
- `context.md`
- `docs/superpowers/CURRENT.md`
- `docs/superpowers/testing/test_cases/TC-026-mvp-drive-docs-save.md`
- `docs/superpowers/testing/test_cases/TC-023-mvp-drive-repo-oauth.md`
- `docs/superpowers/testing/test_cases/TC-024-mvp-sad-preview-it-readiness.md`
- `docs/superpowers/development/03_data_model_and_output_schema.md`
- `docs/superpowers/development/04_google_cloud_setup_runbook.md`
- `docs/superpowers/development/05_development_workflow.md`
- `docs/superpowers/development/07_decision_log.md`

## Scope Lock

In scope:

- Local/fake SAD save path only.
- Authenticated `POST /sad/save`.
- In-memory save records with stable IDs and idempotency.
- Fake Google Doc artifact ID, URL, and project-local path.
- `_SADify` manifest and change-log artifacts.
- Source artifact references from already-uploaded `SRC-` source records when sources exist.
- Frontend save action after a preview exists.
- Backend and frontend tests before implementation.
- TC-026 documentation update only after tests and manual smoke pass.

Out of scope:

- Live Google Drive writes.
- Live Google Docs writes.
- OAuth authorization-code exchange.
- Secret Manager token storage or writes.
- Google Cloud API enablement.
- Dependency additions.
- TC-025 wiki approval.
- TC-027 deployment.
- Creating a separate TC-026A test file.

Forward reference:

- A future TC-026B document may cover the live Google Drive, Google Docs, OAuth exchange, and Secret Manager slice after this local contract passes and the user explicitly approves cloud-touching work.

## Required Endpoint Contract

Endpoint:

```text
POST /sad/save
```

Authentication:

```text
Authorization: Bearer <Firebase ID token>
```

Request body:

```json
{
  "preview_id": "SP-000001"
}
```

Stable rejection cases:

| Case | HTTP status | Stable code | Message |
| --- | --- | --- | --- |
| Unsigned-in or invalid auth header | `401` | `SAD_SAVE_AUTH_REQUIRED` | `Sign in before saving the SAD preview.` |
| Active repo missing | `409` | `SAD_SAVE_REPO_REQUIRED` | `Connect a Google Drive project repo before saving.` |
| Latest repo is disconnected | `409` | `SAD_SAVE_REPO_DISCONNECTED` | `Reconnect Google Drive before saving.` |
| Request has no preview ID | `400` | `SAD_SAVE_PREVIEW_REQUIRED` | `Generate a SAD preview before saving.` |
| Preview ID does not exist | `404` | `SAD_SAVE_PREVIEW_NOT_FOUND` | `This SAD preview is no longer available. Generate it again before saving.` |

Idempotency key:

```text
(user_id, repo_id, preview_id, preview_revision)
```

Implementation detail:

```text
user_id = authenticated Firebase uid
repo_id = DriveRepoRecord.grant_id
preview_id = SadPreviewRecord.preview_id
preview_revision = SadPreviewRecord.created_at.isoformat()
```

Same idempotency key returns the same `SadSaveRecord`. Double-clicking Save never creates two save records or two artifact sets.

## Pydantic Schema Contract

Modify:

```text
D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\schemas.py
```

Add these models.

### `SadSaveRequest`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `preview_id` | `str | None` | No | Route checks missing/blank values so it can return `SAD_SAVE_PREVIEW_REQUIRED` instead of an unstructured validation error. |

### `SadSaveArtifact`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `artifact_id` | `str` | Yes | Stable local artifact ID such as `SA-000001`. |
| `artifact_type` | `Literal["google_doc", "manifest", "change_log", "source_reference"]` | Yes | Local/fake artifact category. |
| `title` | `str` | Yes | Human-readable artifact title. |
| `path` | `str` | Yes | Project repo path such as `SAD/SAD-SP-000001-SV-000001.google_doc`. |
| `file_id` | `str | None` | Yes | Fake Google/Drive-style ID for local slice, such as `LOCAL-GDOC-000001`; `None` only if the artifact intentionally has no file identity. |
| `url` | `str | None` | Yes | Fake link for local slice. Google Doc artifact uses `https://docs.google.com/document/d/LOCAL-GDOC-000001/edit`. |
| `mime_type` | `str | None` | Yes | Examples: `application/vnd.google-apps.document`, `application/json`, `text/plain`. |
| `source_ids` | `list[str]` | Yes | Empty for non-source artifacts; contains `SRC-` IDs for source reference artifacts. |
| `created_at` | `datetime` | Yes | Save timestamp. |

### `SadSaveManifest`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `manifest_id` | `str` | Yes | Stable manifest ID such as `SM-000001`. |
| `repo_grant_id` | `str` | Yes | Connected Drive repo grant ID. |
| `repo_folder_id` | `str` | Yes | Connected repo folder ID. |
| `repo_folder_name` | `str` | Yes | Connected repo folder name. |
| `preview_id` | `str` | Yes | Saved preview ID. |
| `preview_revision` | `str` | Yes | `SadPreviewRecord.created_at.isoformat()`. |
| `analysis_id` | `str | None` | Yes | Original analysis ID from preview record. |
| `requirement_text` | `str` | Yes | Clean requirement text stored on the preview record. |
| `sad_title` | `str` | Yes | Preview title. |
| `preview_section_count` | `int` | Yes | Number of SAD sections. |
| `preview_assumption_count` | `int` | Yes | Number of assumptions. |
| `preview_open_question_count` | `int` | Yes | Number of open questions. |
| `preview_source_references` | `list[str]` | Yes | Source refs from the preview. |
| `source_ids` | `list[str]` | Yes | Resolved uploaded source IDs included in the save manifest. |
| `artifact_paths` | `list[str]` | Yes | Paths for all local save artifacts. |
| `saved_at` | `datetime` | Yes | Save timestamp. |

### `SadSaveRecord`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `save_id` | `str` | Yes | Stable save ID such as `SV-000001`. |
| `idempotency_key` | `str` | Yes | Joined key from `owner_uid`, `repo_grant_id`, `preview_id`, and `preview_revision`. |
| `owner_uid` | `str` | Yes | Authenticated Firebase user ID. |
| `owner_email` | `str | None` | Yes | Authenticated email if available. |
| `project_id` | `str` | Yes | Project ID from active repo record. |
| `repo_grant_id` | `str` | Yes | Active repo grant ID. |
| `repo_folder_id` | `str` | Yes | Active repo folder ID. |
| `repo_folder_name` | `str` | Yes | Active repo folder name. |
| `preview_id` | `str` | Yes | Saved preview ID. |
| `preview_revision` | `str` | Yes | Preview revision string. |
| `status` | `Literal["saved"]` | Yes | Local slice only creates successful local saves. |
| `sad_doc` | `SadSaveArtifact` | Yes | The primary fake Google Doc artifact. |
| `artifacts` | `list[SadSaveArtifact]` | Yes | Includes SAD doc, manifest, change log, and source refs. |
| `manifest` | `SadSaveManifest` | Yes | Save manifest. |
| `change_summary` | `str` | Yes | User-facing summary. |
| `source_artifact_references` | `list[SadSaveArtifact]` | Yes | Source reference artifacts created from uploaded `SRC-` records. |
| `created_at` | `datetime` | Yes | First save timestamp. |
| `updated_at` | `datetime` | Yes | Same as `created_at` for current local slice. |

### `SadSaveApiResponse`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `saved` | `bool` | Yes | `true` for successful local save. |
| `record` | `SadSaveRecord` | Yes | Complete save record. |
| `message` | `str` | Yes | User-facing save message. |

## Files To Change

Backend:

- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\schemas.py`
- Create: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\services\sad_save.py`
- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\services\drive_repo.py`
- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\routes\sad.py`
- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\main.py`
- Test: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\api\test_sad_save.py`

Frontend:

- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\src\lib\api.ts`
- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\src\components\SadPreviewPanel.tsx`
- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\src\components\WorkspaceShell.tsx`
- Test: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\test_mvp_sad_save_ui.py`

Docs, only after tests and manual smoke pass:

- Modify: `D:\GoogleCloudHack\docs\superpowers\testing\test_cases\TC-026-mvp-drive-docs-save.md`
- Modify: `D:\GoogleCloudHack\docs\superpowers\CURRENT.md`
- Modify: `D:\GoogleCloudHack\docs\superpowers\testing\test_case_index.md`
- Modify: `D:\GoogleCloudHack\docs\superpowers\development\07_decision_log.md`

## Task 0: Approval Gate

**Files:**

- Read: `D:\GoogleCloudHack\docs\superpowers\plans\2026-05-25-tc026-local-sad-save.md`

- [ ] **Step 0.1: Wait for user approval**

Do not modify code until the user explicitly approves this plan.

- [ ] **Step 0.2: Confirm worktree**

Run:

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
git status --short
git log --oneline -8
```

Expected:

```text
No unexpected uncommitted code changes owned by the user.
Latest commits include the Phase 4 Q&A/SAD stabilization work.
```

If unrelated user changes exist, leave them untouched and work around them.

## Task 1: Backend Tests First

**Files:**

- Create: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\api\test_sad_save.py`

- [ ] **Step 1.1: Write `test_sad_save_success_creates_local_artifacts`**

Test setup:

```python
from fastapi.testclient import TestClient

from sadify_api.main import create_app
from sadify_api.services.auth import VerifiedFirebaseUser
from sadify_api.services.drive_repo import DriveRepoRepository
from sadify_api.services.sad_preview import SadPreviewRepository
from sadify_api.services.sad_save import SadSaveRepository
from tests.api.test_sad_preview import VALID_PREVIEW


class AcceptingTokenVerifier:
    def verify_id_token(self, id_token: str) -> VerifiedFirebaseUser:
        return VerifiedFirebaseUser(
            uid="firebase-uid-001",
            email="owner@example.com",
            display_name="Project Owner",
            provider="firebase",
        )
```

Assertions:

```text
POST /sad/save returns 200.
Payload.saved is true.
Payload.record.save_id is SV-000001.
Payload.record.preview_id is SP-000001.
Payload.record.sad_doc.artifact_type is google_doc.
Payload.record.sad_doc.file_id is LOCAL-GDOC-000001.
Payload.record.sad_doc.url is https://docs.google.com/document/d/LOCAL-GDOC-000001/edit.
Payload.record.sad_doc.path starts with SAD/.
Payload.record.manifest.artifact_paths contains SAD/, _SADify/manifest, and _SADify/change-log paths.
Payload.record.change_summary names the saved SAD preview and repo folder.
```

- [ ] **Step 1.2: Write `test_sad_save_requires_signed_in_user`**

Assertions:

```text
POST /sad/save without Authorization returns 401.
Response detail.code is SAD_SAVE_AUTH_REQUIRED.
Response detail.message is Sign in before saving the SAD preview.
```

- [ ] **Step 1.3: Write `test_sad_save_blocks_without_active_repo`**

Assertions:

```text
Signed-in POST /sad/save with an existing preview but no active repo returns 409.
Response detail.code is SAD_SAVE_REPO_REQUIRED.
```

- [ ] **Step 1.4: Write `test_sad_save_blocks_disconnected_repo`**

Assertions:

```text
Connect repo.
Disconnect repo.
Signed-in POST /sad/save returns 409.
Response detail.code is SAD_SAVE_REPO_DISCONNECTED.
```

- [ ] **Step 1.5: Write `test_sad_save_requires_preview_id`**

Assertions:

```text
Signed-in POST /sad/save with {} returns 400.
Response detail.code is SAD_SAVE_PREVIEW_REQUIRED.
```

- [ ] **Step 1.6: Write `test_sad_save_rejects_unknown_preview_id`**

Assertions:

```text
Signed-in POST /sad/save with preview_id SP-999999 returns 404.
Response detail.code is SAD_SAVE_PREVIEW_NOT_FOUND.
```

- [ ] **Step 1.7: Write `test_sad_save_is_idempotent_for_same_preview_revision`**

Assertions:

```text
Two identical POST /sad/save calls return 200.
First response record.save_id equals second response record.save_id.
First response record.sad_doc.file_id equals second response record.sad_doc.file_id.
SadSaveRepository stores one record for the key.
```

- [ ] **Step 1.8: Write `test_sad_save_includes_uploaded_source_refs_when_sources_exist`**

Use `SourceRepository.save_extracted_source(...)` to create `SRC-000001`, then save a preview whose `source_references` includes `SRC-000001`.

Assertions:

```text
Payload.record.manifest.source_ids contains SRC-000001.
Payload.record.source_artifact_references has one artifact.
That artifact artifact_type is source_reference.
That artifact source_ids is ["SRC-000001"].
That artifact path starts with Sources/.
```

- [ ] **Step 1.9: Run backend save tests and verify they fail before implementation**

Run:

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
set "PYTHONPATH=services\api\src;src;."
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_sad_save.py -q
```

Expected:

```text
Tests fail because SadSaveRepository, schemas, and POST /sad/save do not exist yet.
```

## Task 2: Add Backend Schemas

**Files:**

- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\schemas.py`
- Test: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\api\test_sad_save.py`

- [ ] **Step 2.1: Add imports if needed**

`schemas.py` already imports `datetime`, `Any`, `Literal`, `BaseModel`, `ConfigDict`, and `Field`. Reuse these imports.

- [ ] **Step 2.2: Add the five SAD save models**

Add the models exactly as listed in the Pydantic Schema Contract section:

```text
SadSaveRequest
SadSaveArtifact
SadSaveManifest
SadSaveRecord
SadSaveApiResponse
```

Use `ApiModel` as the base class for all five models.

- [ ] **Step 2.3: Run backend save tests**

Run:

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
set "PYTHONPATH=services\api\src;src;."
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_sad_save.py -q
```

Expected:

```text
Schema import failures are resolved.
Repository and route tests still fail.
```

## Task 3: Add Local SadSaveRepository And Artifact Composer

**Files:**

- Create: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\services\sad_save.py`
- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\services\drive_repo.py`
- Test: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\api\test_sad_save.py`

- [ ] **Step 3.1: Create `sad_save.py` with fake-store IDs**

The module must provide:

```text
class SadSaveRepository
def get_sad_save_repository() -> SadSaveRepository
```

Repository state:

```text
_records: dict[str, SadSaveRecord]
_by_idempotency_key: dict[str, str]
_next_save_number: int
_next_artifact_number: int
_next_manifest_number: int
_next_fake_doc_number: int
```

ID formats:

```text
SV-000001
SA-000001
SM-000001
LOCAL-GDOC-000001
```

- [ ] **Step 3.2: Implement idempotent save method**

Method signature:

```python
def save_preview(
    self,
    *,
    owner_uid: str,
    owner_email: str | None,
    repo: DriveRepoRecord,
    preview_record: SadPreviewRecord,
    sources: list[SourceRecord],
    saved_at: datetime | None = None,
) -> SadSaveRecord:
```

Behavior:

```text
Compute preview_revision from preview_record.created_at.isoformat().
Compute idempotency_key from owner_uid, repo.grant_id, preview_record.preview_id, preview_revision.
If key exists, return the existing record.
Otherwise create a new SadSaveRecord and store it under both save_id and idempotency key.
```

- [ ] **Step 3.3: Compose required artifacts**

Primary SAD doc:

```text
artifact_type = google_doc
title = preview_record.preview.title
path = SAD/SAD-{preview_id}-{save_id}.google_doc
file_id = LOCAL-GDOC-000001
url = https://docs.google.com/document/d/LOCAL-GDOC-000001/edit
mime_type = application/vnd.google-apps.document
source_ids = resolved source IDs
```

Manifest:

```text
artifact_type = manifest
title = _SADify manifest for {save_id}
path = _SADify/manifest-{save_id}.json
mime_type = application/json
```

Change log:

```text
artifact_type = change_log
title = _SADify change log for {save_id}
path = _SADify/change-log-{save_id}.json
mime_type = application/json
```

Source references:

```text
artifact_type = source_reference
title = Source reference {source_id}: {original_file_name}
path = Sources/{source_id}-{original_file_name}.source-ref.json
mime_type = application/json
source_ids = [source_id]
```

Sanitize source file names for paths by replacing `/`, `\`, and repeated whitespace with `-`.

- [ ] **Step 3.4: Add disconnected repo lookup support**

Modify `DriveRepoRepository` with:

```python
def get_latest_repo(self, owner_uid: str) -> DriveRepoRecord | None:
```

Behavior:

```text
Return active repo if present.
Otherwise return the most recent stored repo owned by that user.
Return None if the user never connected a repo.
```

This supports `SAD_SAVE_REPO_DISCONNECTED` after `/drive/repo/disconnect` removes the active repo.

- [ ] **Step 3.5: Run backend save tests**

Run:

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
set "PYTHONPATH=services\api\src;src;."
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_sad_save.py -q
```

Expected:

```text
Repository-only assertions pass if directly exercised.
Route assertions still fail until POST /sad/save is wired.
```

## Task 4: Add POST /sad/save To Existing SAD Router

**Files:**

- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\routes\sad.py`
- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\services\api\src\sadify_api\main.py`
- Test: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\api\test_sad_save.py`

- [ ] **Step 4.1: Extend `create_sad_router` dependencies**

Current signature:

```python
def create_sad_router(
    model: SadPreviewModel,
    repository: SadPreviewRepository,
) -> APIRouter:
```

Change to include:

```python
def create_sad_router(
    model: SadPreviewModel,
    repository: SadPreviewRepository,
    token_verifier: TokenVerifier,
    drive_repo_repository: DriveRepoRepository,
    source_repository: SourceRepository,
    sad_save_repository: SadSaveRepository,
) -> APIRouter:
```

Keep `POST /sad/preview` behavior unchanged.

- [ ] **Step 4.2: Add local error helper**

Add a helper inside `routes/sad.py`:

```python
def _sad_save_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )
```

- [ ] **Step 4.3: Add authenticated `POST /sad/save`**

Route signature:

```python
@router.post("/save", response_model=SadSaveApiResponse)
def save_preview(
    request: SadSaveRequest,
    authorization: str | None = Header(default=None),
) -> SadSaveApiResponse:
```

Validation order:

```text
1. Verify auth; on auth failure return SAD_SAVE_AUTH_REQUIRED.
2. Check preview_id is present and non-blank; otherwise return SAD_SAVE_PREVIEW_REQUIRED.
3. Read active repo with get_active_repo(user.uid).
4. If no active repo, read latest repo with get_latest_repo(user.uid).
5. If latest repo exists and status is disconnected or saves_blocked is true, return SAD_SAVE_REPO_DISCONNECTED.
6. If no latest repo exists, return SAD_SAVE_REPO_REQUIRED.
7. Read preview from SadPreviewRepository.get_preview(preview_id).
8. If missing, return SAD_SAVE_PREVIEW_NOT_FOUND.
9. Resolve uploaded sources by filtering preview.preview.source_references for IDs that start with SRC- and exist in SourceRepository.
10. Call SadSaveRepository.save_preview(...).
11. Return SadSaveApiResponse(saved=True, record=record, message="SAD preview saved to the local project repo record.").
```

- [ ] **Step 4.4: Wire repository in `main.py`**

Add optional parameter:

```python
sad_save_repository: SadSaveRepository | None = None,
```

Instantiate:

```python
sad_save_repository = sad_save_repository or SadSaveRepository()
```

Update router include:

```python
app.include_router(
    create_sad_router(
        sad_preview_model,
        sad_preview_repository,
        token_verifier,
        drive_repo_repository,
        source_repository,
        sad_save_repository,
    )
)
```

- [ ] **Step 4.5: Run backend save tests**

Run:

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
set "PYTHONPATH=services\api\src;src;."
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_sad_save.py -q
```

Expected:

```text
All tests in tests\api\test_sad_save.py pass.
```

- [ ] **Step 4.6: Run focused backend regression**

Run:

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
set "PYTHONPATH=services\api\src;src;."
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_sad_save.py tests\api\test_sad_preview.py tests\api\test_drive_repo.py -q
```

Expected:

```text
All focused backend tests pass.
```

- [ ] **Step 4.7: Commit backend slice**

Run:

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
git add services\api\src\sadify_api\schemas.py services\api\src\sadify_api\services\sad_save.py services\api\src\sadify_api\services\drive_repo.py services\api\src\sadify_api\routes\sad.py services\api\src\sadify_api\main.py tests\api\test_sad_save.py
git commit -m "feat(sad): add local SAD save contract"
```

Expected:

```text
Commit succeeds.
```

## Task 5: Frontend Tests First

**Files:**

- Create: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\test_mvp_sad_save_ui.py`

- [ ] **Step 5.1: Write `test_sad_save_ui_files_exist`**

Expected files:

```text
apps/web/src/components/SadPreviewPanel.tsx
apps/web/src/components/WorkspaceShell.tsx
apps/web/src/lib/api.ts
```

- [ ] **Step 5.2: Write `test_sad_save_api_contract_is_wired`**

Assertions:

```text
api.ts contains export type SadSaveApiResponse.
api.ts contains export async function saveSadPreview.
api.ts contains /sad/save.
api.ts sends Authorization: Bearer.
api.ts sends preview_id.
```

- [ ] **Step 5.3: Write `test_sad_save_button_renders_after_preview`**

Assertions against `SadPreviewPanel.tsx`:

```text
Panel imports saveSadPreview.
Panel contains Save to project repo.
Panel uses previewResponse before rendering/enabling the save action.
Panel contains getFirebaseAuth or the existing auth helper used to obtain the current user token.
```

- [ ] **Step 5.4: Write `test_sad_save_renders_saved_and_error_states`**

Assertions against `SadPreviewPanel.tsx`:

```text
Panel contains Saved to project repo.
Panel renders record.sad_doc.url.
Panel renders record.sad_doc.path.
Panel renders save error message text.
```

- [ ] **Step 5.5: Write `test_workspace_tracking_updates_after_sad_save`**

Assertions against `WorkspaceShell.tsx`:

```text
WorkspaceShell imports SadSaveApiResponse.
WorkspaceShell has applySadSaved.
SadPreviewPanel receives onSadSaved.
projectStatus includes a saved SAD doc path or link after save.
```

- [ ] **Step 5.6: Run frontend static tests and verify they fail before implementation**

Run:

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\test_mvp_sad_save_ui.py -q
```

Expected:

```text
Tests fail because frontend save API and UI are not wired yet.
```

## Task 6: Frontend Save API And UI

**Files:**

- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\src\lib\api.ts`
- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\src\components\SadPreviewPanel.tsx`
- Modify: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web\src\components\WorkspaceShell.tsx`
- Test: `D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\tests\test_mvp_sad_save_ui.py`

- [ ] **Step 6.1: Add TypeScript save types**

Add types matching backend response:

```typescript
export type SadSaveArtifact = {
  artifact_id: string;
  artifact_type: "google_doc" | "manifest" | "change_log" | "source_reference";
  title: string;
  path: string;
  file_id: string | null;
  url: string | null;
  mime_type: string | null;
  source_ids: string[];
  created_at: string;
};

export type SadSaveManifest = {
  manifest_id: string;
  repo_grant_id: string;
  repo_folder_id: string;
  repo_folder_name: string;
  preview_id: string;
  preview_revision: string;
  analysis_id: string | null;
  requirement_text: string;
  sad_title: string;
  preview_section_count: number;
  preview_assumption_count: number;
  preview_open_question_count: number;
  preview_source_references: string[];
  source_ids: string[];
  artifact_paths: string[];
  saved_at: string;
};

export type SadSaveRecord = {
  save_id: string;
  idempotency_key: string;
  owner_uid: string;
  owner_email: string | null;
  project_id: string;
  repo_grant_id: string;
  repo_folder_id: string;
  repo_folder_name: string;
  preview_id: string;
  preview_revision: string;
  status: "saved";
  sad_doc: SadSaveArtifact;
  artifacts: SadSaveArtifact[];
  manifest: SadSaveManifest;
  change_summary: string;
  source_artifact_references: SadSaveArtifact[];
  created_at: string;
  updated_at: string;
};

export type SadSaveApiResponse = {
  saved: boolean;
  record: SadSaveRecord;
  message: string;
};
```

- [ ] **Step 6.2: Add `saveSadPreview(previewId, idToken)`**

Function signature:

```typescript
export async function saveSadPreview(
  previewId: string,
  idToken: string,
): Promise<SadSaveApiResponse>
```

Fetch contract:

```text
POST `${baseUrl}/sad/save`
Headers:
  Authorization: Bearer ${idToken}
  Content-Type: application/json
Body:
  {"preview_id": previewId}
```

Use `readBackendError` for all non-OK responses.

- [ ] **Step 6.3: Update `SadPreviewPanel` props and state**

Add prop:

```typescript
onSadSaved: (response: SadSaveApiResponse) => void;
```

Add state:

```typescript
const [saveResponse, setSaveResponse] = useState<SadSaveApiResponse | null>(null);
const [saveMessage, setSaveMessage] = useState("");
const [isSaving, setIsSaving] = useState(false);
```

Reset `saveResponse` and `saveMessage` in the same `useEffect` that clears stale preview state.

- [ ] **Step 6.4: Add save handler**

Behavior:

```text
If no previewResponse, show Generate a SAD preview before saving.
If no current Firebase user, show Sign in before saving the SAD preview.
Otherwise get ID token, call saveSadPreview(previewResponse.preview_id, idToken), store response, call onSadSaved(response), and show Saved to project repo.
On error, show backend message.
```

Use the existing Firebase helper pattern from the app. Do not add a new auth library.

- [ ] **Step 6.5: Render save button and saved state**

Show the button only when `previewResponse` exists:

```text
Save to project repo
```

Saved state text:

```text
Saved to project repo
{record.sad_doc.title}
{record.sad_doc.path}
{record.sad_doc.url}
{record.change_summary}
```

Error state:

```text
Show saveMessage when it contains a backend or auth error.
```

- [ ] **Step 6.6: Update `WorkspaceShell` tracking**

Add:

```typescript
function applySadSaved(response: SadSaveApiResponse) {
  setWorkspaceState((current) => ({
    ...current,
    changeSummary: response.record.change_summary,
    projectStatus: [
      `SAD saved: ${response.record.save_id}`,
      `Google Doc placeholder: ${response.record.sad_doc.path}`,
      `Repo: ${response.record.repo_folder_name}`,
      response.record.source_artifact_references.length
        ? `${response.record.source_artifact_references.length} source reference(s) linked`
        : "No uploaded source references linked",
    ],
  }));
}
```

Pass:

```text
onSadSaved={applySadSaved}
```

- [ ] **Step 6.7: Run frontend static tests**

Run:

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\test_mvp_sad_save_ui.py -q
```

Expected:

```text
All SAD save frontend static tests pass.
```

- [ ] **Step 6.8: Run TypeScript check**

Run:

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web
npx -y tsc --noEmit
```

Expected:

```text
No TypeScript errors.
```

- [ ] **Step 6.9: Commit frontend slice**

Run:

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
git add apps\web\src\lib\api.ts apps\web\src\components\SadPreviewPanel.tsx apps\web\src\components\WorkspaceShell.tsx tests\test_mvp_sad_save_ui.py
git commit -m "feat(web): add local SAD save action"
```

Expected:

```text
Commit succeeds.
```

## Task 7: Full Verification And Manual Smoke

**Files:**

- No new implementation files.

- [ ] **Step 7.1: Run focused backend and frontend tests**

Run:

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
set "PYTHONPATH=services\api\src;src;."
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests\api\test_sad_save.py tests\api\test_sad_preview.py tests\api\test_drive_repo.py tests\test_mvp_sad_save_ui.py tests\test_mvp_sad_preview_it_readiness_ui.py tests\test_mvp_drive_repo_oauth_ui.py -q
```

Expected:

```text
All focused tests pass.
```

- [ ] **Step 7.2: Run full Python regression**

Run:

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
set "PYTHONPATH=services\api\src;src;."
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest -q
```

Expected:

```text
All Python tests pass.
```

- [ ] **Step 7.3: Run TypeScript check**

Run:

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web
npx -y tsc --noEmit
```

Expected:

```text
No TypeScript errors.
```

- [ ] **Step 7.4: Run local manual smoke**

Backend command:

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold
set "PYTHONPATH=services\api\src;src;."
set "FIREBASE_PROJECT_ID=sadify"
set "GOOGLE_CLOUD_PROJECT=sadify"
D:\GoogleCloudHack\.venv\Scripts\uvicorn.exe sadify_api.main:app --host 0.0.0.0 --port 8000
```

Frontend command:

```cmd
cd /d D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold\apps\web
npm run dev
```

Smoke path:

```text
1. Sign in.
2. Connect local Drive repo using the current config-aware fake/local path.
3. Upload a source file or use text-only input.
4. Run analysis until draft-ready.
5. Generate SAD preview.
6. Click Save to project repo.
7. Confirm UI shows Saved to project repo, fake Google Doc link/path, repo name, and source refs when sources exist.
8. Click Save again and confirm the same save ID is shown.
9. Disconnect Drive repo.
10. Try Save again and confirm the UI shows the disconnected/reconnect error.
```

Expected:

```text
Backend logs show POST /sad/save 200 for valid saves.
Double-click/repeat save returns the same save ID.
Disconnected repo save returns 409 with SAD_SAVE_REPO_DISCONNECTED.
No live Drive, Docs, OAuth exchange, Secret Manager, or dependency install occurs.
```

## Task 8: Documentation Updates After Pass

**Files:**

- Modify: `D:\GoogleCloudHack\docs\superpowers\testing\test_cases\TC-026-mvp-drive-docs-save.md`
- Modify: `D:\GoogleCloudHack\docs\superpowers\CURRENT.md`
- Modify: `D:\GoogleCloudHack\docs\superpowers\testing\test_case_index.md`
- Modify: `D:\GoogleCloudHack\docs\superpowers\development\07_decision_log.md`

- [ ] **Step 8.1: Update TC-026**

Update these sections only after Task 7 passes:

```text
Real Output
Differences / Issues
Evidence
Decision
```

Record:

```text
Endpoint implemented: POST /sad/save.
Local/fake Google Doc artifact created.
_SADify manifest and change-log artifacts created.
Source references included when uploaded sources exist.
Idempotent repeated save returns same record.
No live Google writes or token storage happened.
Focused tests, full pytest, TypeScript, and manual smoke results.
```

- [ ] **Step 8.2: Update CURRENT.md status line**

Update Phase 5 status to say TC-026 local/fake save path passed, while live Drive/Docs remains future TC-026B and TC-025/TC-027 remain blocked until user approval.

- [ ] **Step 8.3: Update test case index**

Update TC-026 row:

```text
Status: Passed for local/fake save path
Date: 2026-05-25
Notes: local/fake save contract passed; live Drive/Docs slice deferred to future TC-026B
```

- [ ] **Step 8.4: Append decision-log entry**

Append to `Change Notes`:

```text
2026-05-25 | Split TC-026 into local-first save contract and future live Drive/Docs slice | The local/fake save path proves product behavior and idempotency without cloud writes; live OAuth/Drive/Docs/Secret Manager work remains future TC-026B after explicit approval | TC-026, CURRENT, test index
```

Do not change confirmed decisions for TC-025 or TC-027 in this checkpoint.

- [ ] **Step 8.5: Commit docs**

Run:

```cmd
cd /d D:\GoogleCloudHack
git status --short
```

If these docs are tracked in the current repo, commit them. If docs remain outside the MVP worktree commit flow, leave them uncommitted and report the updated file paths.

## Stop Rules

Stop immediately if any of these happens:

- The plan is not yet approved by the user.
- A change would enable Google Cloud APIs.
- A change would add Python or npm dependencies.
- A change would perform live OAuth exchange.
- A change would write to Google Drive or Google Docs.
- A change would write, create, update, or delete Secret Manager secrets.
- A change would start TC-025 wiki approval.
- A change would start TC-027 deployment.
- Billing, IAM, OAuth scope, or token-storage behavior becomes necessary to proceed.
- Source traceability is missing from saved artifacts when uploaded sources exist.
- The save path cannot produce stable error codes.
- Idempotency cannot prevent duplicate artifacts on repeat save.

Honor `CLAUDE.md` sections 1, 2, 4.1, 4.2, 4.3, 5.1, 6, and 7.1 throughout execution. In practical terms for this checkpoint:

```text
Read current docs and code before editing.
Keep changes scoped to TC-026 local/fake save only.
Prefer existing repo patterns.
Do tests before implementation.
Do not add unrelated refactors.
Do not touch secrets or live cloud resources.
Update test-case evidence before claiming the checkpoint passed.
Stop after the checkpoint and wait for the user's next approval.
```

## Verification Summary Required Before Completion

Before claiming TC-026 local/fake save is complete, report:

```text
Backend focused test count and result.
Frontend static test count and result.
Full Python regression count and result.
TypeScript result.
Manual smoke result.
Whether duplicate save returned the same save ID.
Whether disconnected repo returned SAD_SAVE_REPO_DISCONNECTED.
Confirmation that no live Drive, Docs, OAuth exchange, Secret Manager write, dependency install, Cloud API enablement, wiki approval, or deployment occurred.
```

