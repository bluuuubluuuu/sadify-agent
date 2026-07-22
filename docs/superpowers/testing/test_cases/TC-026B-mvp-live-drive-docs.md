# TC-026B MVP Live Drive/Docs Save

Date Created: 2026-05-25
Last Updated: 2026-05-25
Status: Passed (live OAuth + Drive write + Docs write + Secret Manager
token storage verified end-to-end)

## Purpose

Promote the local/fake SAD save path from TC-026 to a real Google Drive +
Google Docs write, with the OAuth refresh token stored in Secret Manager.
TC-026's local mode remains the default; live mode is opt-in via a
double-gated env switch.

## Inputs

- Signed-in Firebase user.
- Live OAuth Web client `SADify Web (TC-026B)` (Client ID
  `594758969655-0md22e7bs1hvjjg1ihpokvvtpuarq6pp.apps.googleusercontent.com`).
- OAuth client secret stored in Secret Manager as
  `sadify-drive-oauth-client-secret` v1.
- Drive API and Docs API enabled on project `sadify`.
- Both `sadify-agent-sa` and `firebase-adminsdk-fbsvc` granted Secret
  Manager Accessor on the OAuth client secret AND project-level Secret
  Manager Admin for per-user token writes.
- Draft-ready SAD preview from the existing analysis flow.

## Preconditions

- TC-026 local/fake save path passed on 2026-05-25.
- Cloud preparation completed per runbook section
  "TC-026B Live Drive/Docs Setup (Completed 2026-05-25)".
- Implementation landed in commit `ee87b18`
  (feat(drive): live drive/docs save behind SADIFY_DRIVE_MODE=live).

## Scope

In scope:

1. Live OAuth authorization-code exchange via GIS popup mode.
2. Refresh token persistence in Secret Manager
   (`sadify-drive-token-<firebase-uid>`).
3. Live Drive folder create-or-find (`SADify Projects`).
4. Live Markdown upload via Drive `files.create` with MIME conversion to
   Google Doc.
5. Live disconnect: deletes the user's token secret from Secret Manager.
6. Idempotency: a repeat save returns the cached record without
   re-uploading.
7. Local-mode behavior unchanged from TC-026.

Out of scope:

- Drive Picker / folder browsing UI.
- Doc-level styling via Docs API `batchUpdate`.
- Retry/backoff on Drive errors.
- TC-025 wiki update approval.
- TC-027 Cloud Run deployment.

## Steps

1. Set live-mode env on the backend:
   `SADIFY_DRIVE_MODE=live`,
   `SADIFY_TC026B_LIVE=1`,
   `SADIFY_GOOGLE_OAUTH_CLIENT_ID=594758969655-0md22e7bs1hvjjg1ihpokvvtpuarq6pp.apps.googleusercontent.com`,
   `OAUTHLIB_RELAX_TOKEN_SCOPE=1`.
2. Set `NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID` on the frontend.
3. Restart both servers; confirm the "Connect (local dev)" button
   disappears in the UI.
4. Click `Connect Google Drive`, complete the consent popup
   (accept the unverified-app warning), and confirm panel shows
   "Project repo connected. Saves are now allowed for this repo."
5. Run analysis to draft-ready and generate a SAD preview.
6. Click `Save to project repo` and confirm the saved card shows a real
   `https://docs.google.com/document/d/...` URL.
7. Visit https://drive.google.com and confirm the `SADify Projects`
   folder exists and contains the new Doc.
8. Click `Disconnect Google Drive`.
9. Try `Save to project repo` again and confirm 409
   `Reconnect Google Drive before saving.`
10. In Secret Manager console, confirm the per-user
    `sadify-drive-token-<uid>` secret has been deleted.

## Expected Output

- `POST /drive/repo/connect` returns 200 in live mode.
- `POST /sad/save` returns 200 and persists a real Google Doc.
- Saved card shows a 40+ character Drive file ID and a working Doc URL.
- The Doc opens and renders the SAD content (title, sections, body
  paragraphs, assumptions).
- `POST /drive/repo/disconnect` returns 200, deletes the per-user
  refresh-token secret, and blocks future saves with
  `SAD_SAVE_REPO_DISCONNECTED` until reconnect.
- Local-mode regression (332 pytest + clean TypeScript) continues to
  pass.

## Real Output

Live verification on 2026-05-25 with Firebase user
`<owner-uid>` (<owner-email>):

```text
POST /auth/session                 200
POST /drive/repo/connect           200  DG-000001 -> SADify Projects
POST /analysis/requirement (x11)   200  draft-ready reached (score 100)
POST /sad/preview                  200  SP-000001
POST /sad/save                     200  Real Doc 1wy-QWBUGgmpmfiM59X91wy6V-S9lpQpZ582CeMRkn68
POST /drive/repo/disconnect        200  Token secret deleted from Secret Manager
POST /sad/save                     409  SAD_SAVE_REPO_DISCONNECTED after disconnect
```

Saved card on the happy-path save:

```text
Path:    SAD/SAD-SP-000001-SV-000001.google_doc
URL:     https://docs.google.com/document/d/1wy-QWBUGgmpmfiM59X91wy6V-S9lpQpZ582CeMRkn68/edit?usp=drivesdk
Folder:  SADify Projects (visible at root of <owner-email> Drive)
Doc:     opens cleanly with rendered headings, body paragraphs, and the
         "Assumptions" list from the catering-company test scenario.
```

Secret Manager state after disconnect:

```text
sadify-drive-oauth-client-secret    (kept; app-level OAuth client secret)
sadify-drive-token-<owner-uid>     (deleted on disconnect; confirmed gone in console)
```

## Differences / Issues

Three deviations resolved during manual smoke; all are environment-level,
no code changes triggered:

1. The first 502 (`DRIVE_LIVE_MODE_DISABLED`) reminded us that the live
   path is double-gated: both `SADIFY_DRIVE_MODE=live` and
   `SADIFY_TC026B_LIVE=1` must be set. By design; the second gate is a
   safety belt against accidental cloud calls.
2. The second 502 was a missing `SADIFY_GOOGLE_OAUTH_CLIENT_ID`. The
   config defaults this to empty string when the env var is unset; that
   caused `oauthlib.InvalidClientIdError: Could not determine client ID
   from request.` Resolved by setting the env var.
3. The third 502 was an `oauthlib` scope-warning-as-error: Google's GIS
   automatically expands the requested `drive.file` scope to include
   baseline `openid`, `userinfo.email`, `userinfo.profile`. Resolved by
   setting `OAUTHLIB_RELAX_TOKEN_SCOPE=1`.

Cleanup follow-up (tracked separately, not blocking this checkpoint):

- Rename `SADIFY_TC026B_LIVE` to `SADIFY_DRIVE_LIVE_ENABLED` so the env
  var name does not encode a checkpoint label.
- Move `OAUTHLIB_RELAX_TOKEN_SCOPE=1` into `drive_client.py` as
  `os.environ.setdefault(...)` so future runs do not need the shell var.
- Revert the diagnostic `logger.exception("drive_oauth_exchange_failed")`
  line added to `routes/drive.py` during this checkpoint; production
  behavior should not log the chained exception by default.

## Evidence

- Implementation commit: `ee87b18 feat(drive): live drive/docs save
  behind SADIFY_DRIVE_MODE=live`.
- New backend services: `secret_store.py`, `drive_client.py`,
  `sad_markdown.py`.
- Modified backend services: `drive_repo.py`, `sad_save.py`, `config.py`,
  `main.py`, `routes/drive.py`, `routes/sad.py`.
- Approved schema delta: `schemas.py` token_store Literal gains
  `"secret_manager"` (append-only).
- Test counts:
  - `SADIFY_DRIVE_MODE=local` full pytest: 332 passed (was 290 before
    TC-026B; +42 mocked live-mode tests).
  - Default (no env set) pytest: 332 passed.
  - TypeScript: `npx -y tsc --noEmit` clean.
- Live manual smoke: Cases 9 and 10 both passed end-to-end (HTTP
  sequence and Secret Manager state shown above).
- Real Doc ID `1wy-QWBUGgmpmfiM59X91wy6V-S9lpQpZ582CeMRkn68` opens in
  Drive and shows SAD content; folder `SADify Projects` exists.
- Local mode regression: TC-026's Cases 3-8 still pass (verified
  earlier on 2026-05-25 before live mode was enabled).

## Decision

Passed. SADify can now save SAD previews into the user's real Google
Drive as real Google Docs, with refresh tokens stored in Secret Manager
and cleaned up on disconnect. Local-mode behavior is fully preserved as
the default so offline tests, dev runs, and demos without cloud access
continue to work.

Next checkpoint dependencies are unblocked:

- TC-025 wiki update approval now has a real save target.
- TC-027 two-service Cloud Run deploy can proceed once Dockerfiles and
  cloudbuild config are authored.

A separate cleanup commit will land the three follow-up items listed
under "Differences / Issues" without changing behavior.
